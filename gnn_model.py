import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
import os
import math

class GNNScoreModel(torch.nn.Module):
    def __init__(self, num_node_features):
        super(GNNScoreModel, self).__init__()
        self.conv1 = GCNConv(num_node_features, 16)
        self.conv2 = GCNConv(16, 8)
        self.fc = torch.nn.Linear(8, 1)

    def forward(self, data):
        x, edge_index = data.x, data.edge_index

        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        
        # Graph level readout (mean over nodes)
        x = torch.mean(x, dim=0)
        
        # Final score
        score = torch.sigmoid(self.fc(x))
        return score

class GNNManager:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        self.model_path = os.path.join(self.model_dir, "gnn_model.pth")
        
        # GPU detection ONLY for GNN model and SHAP computation
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.model = GNNScoreModel(num_node_features=4).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01)
        
        if os.path.exists(self.model_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                print("Loaded existing GNN model.")
            except Exception as e:
                print(f"Failed to load model: {e}")

    def extract_features(self, scheduler, allocator):
        # We model each Slot as a node.
        # Node features: 
        # 1. room_utilization (avg % of seats filled across rooms)
        # 2. invigilator_load (avg invigilators per room / total available)
        # 3. slot_density (number of subjects in slot / total subjects)
        # 4. gap_days (average gap days between exams for same cohort) -> simplification: 1 if all gap > 2, else 0
        
        nodes = []
        node_idx = {}
        idx = 0
        
        total_subjects = len(scheduler.dl.subject_students)
        
        for ds, allocs in allocator.allocations.items():
            if not allocs: continue
            
            # 1. room_utilization
            total_cap = sum(a['room']['cap'] for a in allocs)
            total_students = sum(len(a['students']) for a in allocs)
            room_utilization = total_students / total_cap if total_cap > 0 else 0
            
            # 2. invigilator_load
            invigs = allocator.invigilator_assignments.get(ds, {})
            total_invigs_assigned = sum(len(v) for v in invigs.values())
            invigilator_load = total_invigs_assigned / max(1, len(scheduler.dl.invigilators_df))
            
            # 3. slot_density
            slot_density = len(allocator.slot_subjects.get(ds, [])) / total_subjects
            
            # 4. gap_days (proxy)
            gap_days = 1.0 # default good
            
            nodes.append([room_utilization, invigilator_load, slot_density, gap_days])
            node_idx[ds] = idx
            idx += 1
            
        if not nodes:
            return None
            
        x = torch.tensor(nodes, dtype=torch.float)
        
        # Edges between slots that are adjacent in time
        edge_index = []
        slots_list = list(node_idx.keys())
        for i in range(len(slots_list)-1):
            edge_index.append([node_idx[slots_list[i]], node_idx[slots_list[i+1]]])
            edge_index.append([node_idx[slots_list[i+1]], node_idx[slots_list[i]]])
            
        if not edge_index:
            edge_index = [[0],[0]] # Self loop if only 1 slot
            
        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        
        return Data(x=x, edge_index=edge_index).to(self.device)

    def train_model(self, data, epochs=100):
        self.model.train()
        best_loss = float('inf')
        
        # Target: maximize room_utilization, minimize slot_density and load
        # Let's define a target score based on features
        # Ideal: high utilization (1.0), low density (0.1), reasonable load
        # For simplicity, we just train it towards a "validity" target which is 1.0 if it's a good schedule.
        # We simulate a target score based on the current data features.
        avg_util = data.x[:, 0].mean()
        target = torch.tensor([float(avg_util)], dtype=torch.float).to(self.device)
        
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            out = self.model(data)
            loss = F.mse_loss(out, target)
            loss.backward()
            self.optimizer.step()
            
            if loss.item() < best_loss:
                best_loss = loss.item()
                torch.save(self.model.state_dict(), self.model_path)
                
        return best_loss
        
    def update_from_repair(self, scheduler, allocator, is_valid):
        # "And the repair part will directly train the .pth or .pt file"
        data = self.extract_features(scheduler, allocator)
        if data:
            self.model.train()
            self.optimizer.zero_grad()
            out = self.model(data)
            target = torch.tensor([1.0 if is_valid else 0.0], dtype=torch.float).to(self.device)
            loss = F.mse_loss(out, target)
            loss.backward()
            self.optimizer.step()
            torch.save(self.model.state_dict(), self.model_path)
