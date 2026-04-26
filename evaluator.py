import numpy as np
import datetime

class Evaluator:
    def __init__(self, scheduler, allocator, validator):
        self.scheduler = scheduler
        self.allocator = allocator
        self.validator = validator
        
    def evaluate(self):
        violations = self.validator.validate()
        num_hard_violations = len(violations)
        
        # Calculate room utilization, empty rooms, single subject rooms
        total_seats = 0
        filled_seats = 0
        empty_rooms = 0
        single_subject_rooms = 0
        
        # Identify all possible rooms from DL
        total_rooms = len(self.allocator.dl.rooms_df)
        used_rooms_count = 0
        
        # Invigilator balance
        invig_loads = {row['EMP_NAME'].strip(): 0 for _, row in self.allocator.dl.invigilators_df.iterrows()}
        
        for ds, allocs in self.allocator.allocations.items():
            used_rooms_count += len(allocs)
            for alloc in allocs:
                total_seats += alloc['room']['cap']
                filled_seats += len(alloc['students'])
                
                subjects = set(st['subject'] for st in alloc['students'])
                if len(subjects) == 1:
                    single_subject_rooms += 1
                    
            if ds in self.allocator.invigilator_assignments:
                for room, invigs in self.allocator.invigilator_assignments[ds].items():
                    for inv in invigs:
                        if inv in invig_loads:
                            invig_loads[inv] += 1
                        else:
                            invig_loads[inv] = 1
                            
        empty_rooms = total_rooms * len(self.scheduler.slots) * len(self.scheduler.valid_dates) - used_rooms_count
        if empty_rooms < 0: empty_rooms = 0
        
        room_utilization = (filled_seats / total_seats) if total_seats > 0 else 0
        
        load_values = list(invig_loads.values())
        invig_balance_score = float(np.var(load_values)) if load_values else 0.0
        
        # Calculate gap score (average gap between exams for the same cohort)
        # We want to minimize the score, so a higher gap is a lower penalty.
        # Let's say target gap is 3. penalty = max(0, 3 - gap)
        gap_penalty = 0
        cohort_dates = {}
        for code, info in self.scheduler.schedule.items():
            d = datetime.datetime.strptime(info['date'], "%d/%m/%Y").date()
            dept = self.allocator.dl.subject_details[code]['dept']
            sem = self.allocator.dl.subject_details[code]['sem']
            key = (dept, sem)
            if key not in cohort_dates:
                cohort_dates[key] = []
            cohort_dates[key].append(d)
            
        for key, dates in cohort_dates.items():
            dates.sort()
            for i in range(1, len(dates)):
                gap = (dates[i] - dates[i-1]).days
                if gap < 3:
                    gap_penalty += (3 - gap)
                    
        # FINAL SCORE = (Hard Violations * 10000) - (Room Util * 100) + (Invig Balance * 10) + (Gap penalty * 10)
        final_score = (num_hard_violations * 10000) - (room_utilization * 100) + (invig_balance_score * 10) + (gap_penalty * 10)
        
        metrics = {
            "hard_constraint_violations": num_hard_violations,
            "room_utilization": room_utilization,
            "invigilator_balance_score": invig_balance_score,
            "student_gap_score": gap_penalty,
            "empty_rooms": empty_rooms,
            "single_subject_rooms": single_subject_rooms,
            "final_score": final_score
        }
        
        return metrics
