import sys
import os
from programs.data_loader import DataLoader
from programs.scheduler import Scheduler
from programs.allocator import Allocator
from programs.csp_validator import CSPValidator
from programs.csp_repair import CSPRepair
from programs.gnn_model import GNNManager
from programs.output_generator import OutputGenerator
from programs.shap_explainer import SHAPExplainer
from programs.evaluator import Evaluator

def generate_and_repair(dl, start_date, end_date, holidays_list, is_training):
    scheduler = Scheduler(dl, start_date, end_date, holidays_list)
    scheduler.generate_base_schedule()
    
    allocator = Allocator(dl, scheduler.schedule)
    allocator.allocate_all()
    
    validator = CSPValidator(dl, scheduler.schedule, allocator.allocations, allocator.invigilator_assignments)
    evaluator = Evaluator(scheduler, allocator, validator)
    
    initial_metrics = evaluator.evaluate()
    initial_violations = initial_metrics['hard_constraint_violations']
    
    prefix = "[TRAIN]" if is_training else "[TEST]"
    print(f"{prefix} Initial violations: {initial_violations}", flush=True)
    
    gnn_manager = GNNManager("models")
    repair_happened = False
    
    if initial_violations > 0:
        repair_happened = True
        repair = CSPRepair(scheduler, allocator, validator, max_iterations=50)
        
        # Auto-correction loop until violations == 0
        iterations = 0
        while True:
            success = repair.repair()
            metrics = evaluator.evaluate()
            if metrics['hard_constraint_violations'] == 0 or iterations >= 3:
                break
            iterations += 1
            
        final_metrics = evaluator.evaluate()
        print(f"{prefix} After repair: {final_metrics['hard_constraint_violations']}", flush=True)
    else:
        final_metrics = initial_metrics
        print(f"{prefix} After repair: 0", flush=True)
        
    print(f"{prefix} Final score: {final_metrics['final_score']}", flush=True)
    
    # Self-learning
    if repair_happened and is_training:
        data = gnn_manager.extract_features(scheduler, allocator)
        if data:
            target = 1.0 if final_metrics['hard_constraint_violations'] == 0 else 0.0
            gnn_manager.model.train()
            gnn_manager.optimizer.zero_grad()
            out = gnn_manager.model(data)
            import torch
            import torch.nn.functional as F
            target_t = torch.tensor([target], dtype=torch.float).to(gnn_manager.device)
            loss = F.mse_loss(out, target_t)
            loss.backward()
            gnn_manager.optimizer.step()
            torch.save(gnn_manager.model.state_dict(), gnn_manager.model_path)
            
    return scheduler, allocator, gnn_manager, final_metrics


def run_training():
    print("\n--- PHASE 0: Data Handling ---")
    dl = DataLoader("data")
    dl.load_all()
    
    start_date = "01/05/2026"
    end_date = "30/05/2026"
    holidays_list = []
    
    scheduler, allocator, gnn_manager, metrics = generate_and_repair(dl, start_date, end_date, holidays_list, is_training=True)

    print("\n--- Model Training ---")
    data = gnn_manager.extract_features(scheduler, allocator)
    if data:
        data_size = len(dl.subject_students) * len(dl.rooms_df)
        rec_epochs = 50 if data_size < 1000 else 200
        print(f"Recommended epochs based on data size: {rec_epochs}")
        try:
            user_epochs = int(input("Enter number of epochs to complete training process: "))
        except:
            user_epochs = rec_epochs
        
        print(f"Training GNN for {user_epochs} epochs...")
        best_loss = gnn_manager.train_model(data, epochs=user_epochs)
        print(f"Training complete. Best loss: {best_loss:.4f}. Best model saved.")
    
    if metrics['hard_constraint_violations'] == 0:
        print("\n--- PHASE 8: Output PDFs ---")
        out_gen = OutputGenerator(scheduler, allocator, "output")
        out_gen.generate_all()
    else:
        print("\n[WARNING] Output skipped: Hard constraint violations exist.")
        
    return scheduler, allocator, gnn_manager

def run_testing():
    print("\n--- PHASE 0: Data Handling ---")
    dl = DataLoader("data")
    dl.load_all()
    
    start_date = "01/05/2026"
    end_date = "30/05/2026"
    holidays_list = []
    
    num_runs = 1
    print(f"\n--- Running {num_runs} Test Configurations ---", flush=True)
    
    scores = []
    best_score = float('inf')
    worst_score = float('-inf')
    best_run = None
    
    for i in range(1, num_runs + 1):
        print(f"\n--- Test Run {i} ---", flush=True)
        scheduler, allocator, gnn_manager, metrics = generate_and_repair(dl, start_date, end_date, holidays_list, is_training=False)
        score = metrics['final_score']
        scores.append(score)
        
        if score < best_score:
            best_score = score
            best_run = (scheduler, allocator, gnn_manager, metrics)
        if score > worst_score:
            worst_score = score
            
    avg_score = sum(scores) / len(scores)
    
    print("\n----------------------------------")
    print("TEST RESULTS")
    print("----------------------------------")
    for i, s in enumerate(scores):
        print(f"Run {i+1}: Score = {s}")
    print(f"Average: {avg_score}")
    print(f"Best: {best_score}")
    print(f"Worst: {worst_score}")
    
    print("\n[TEST] Best schedule found.")
    scheduler, allocator, gnn_manager, metrics = best_run
    
    if metrics['hard_constraint_violations'] == 0:
        print("\n--- PHASE 8: Output PDFs ---")
        out_gen = OutputGenerator(scheduler, allocator, "output")
        out_gen.generate_all()
    else:
        print("\n[WARNING] Output skipped: Hard constraint violations exist.")
        
    return scheduler, allocator, gnn_manager



def main_menu():
    scheduler, allocator, gnn_manager = None, None, None
    while True:
        print("\n==========================================")
        print("   COMPLETE EXAM SCHEDULING SYSTEM")
        print("==========================================")
        print("1. Train Model (Full Pipeline + Repair + Train)")
        print("2. Test Model (Multiple Runs)")
        print("3. Explain Output (SHAP)")
        print("4. Exit")
        choice = input("Enter choice: ").strip()
        
        if choice == '1':
            scheduler, allocator, gnn_manager = run_training()
        elif choice == '2':
            scheduler, allocator, gnn_manager = run_testing()
        elif choice == '3':
            if scheduler is None or gnn_manager is None:
                print("Please run Option 1 or 2 first to generate a schedule.")
            else:
                data = gnn_manager.extract_features(scheduler, allocator)
                if data:
                    explainer = SHAPExplainer(gnn_manager.model, data, "output")
                    explainer.explain()
                else:
                    print("No data available to explain.")
        elif choice == '4':
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()
