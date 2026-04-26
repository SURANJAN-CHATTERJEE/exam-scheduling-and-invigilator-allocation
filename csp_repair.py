import random
import datetime

class CSPRepair:
    def __init__(self, scheduler, allocator, validator, max_iterations=50):
        self.scheduler = scheduler
        self.allocator = allocator
        self.validator = validator
        self.max_iterations = max_iterations
        
    def repair(self):
        iterations = 0
        violations = self.validator.validate()
        
        while violations and iterations < self.max_iterations:
            if iterations == 0:
                from collections import Counter
                types = Counter(v['type'] for v in violations)
                print(f"Iteration {iterations}: {len(violations)} violations found. Types: {dict(types)}", flush=True)
            else:
                print(f"Iteration {iterations}: {len(violations)} violations found.", flush=True)
            # Sort violations by priority (lower number = higher priority)
            violations.sort(key=lambda x: x['priority'])
            
            # Pick the highest priority violation to fix
            v = violations[0]
            
            if v['type'] == 'specialization_conflict':
                # HARD CONSTRAINT: Wrong specialization student seated
                print(f"HARD CONSTRAINT VIOLATION: Removing wrongly assigned student {v['roll']} for subject {v['subject']}")
                # Re-allocate the slot completely to fetch the correct queue from data_loader
                ds = v['slot']
                subjects = self.allocator.slot_subjects.get(ds, [])
                if subjects:
                    self.allocator._allocate_slot(ds, subjects)
                    self.allocator._assign_invigilators(ds)
                
            elif v['type'] == 'dept_sem_clash':
                # Move one of the conflicting subjects to another date
                codes = v['codes']
                subject_to_move = codes[-1] # Pick the last one
                
                # Find a new valid date
                valid_dates = self.scheduler.valid_dates
                current_date = datetime.datetime.strptime(v['date'], "%d/%m/%Y").date()
                
                # Try to find a date that doesn't have this dept-sem
                dept = v['dept']
                sem = v['sem']
                
                moved = False
                for d in valid_dates:
                    if d == current_date:
                        continue
                    # Check if this date already has this dept-sem
                    d_str = d.strftime("%d/%m/%Y")
                    conflict = False
                    for c, info in self.scheduler.schedule.items():
                        if info['date'] == d_str and self.scheduler.dl.subject_details[c]['dept'] == dept and self.scheduler.dl.subject_details[c]['sem'] == sem:
                            conflict = True
                            break
                    if not conflict:
                        # Move to this date
                        self.scheduler.schedule[subject_to_move] = {'date': d_str, 'slot': random.choice(self.scheduler.slots)}
                        moved = True
                        break
                        
                if not moved:
                    # Just pick a random date if no perfect one found (let next iteration handle it)
                    d = random.choice(valid_dates)
                    self.scheduler.schedule[subject_to_move] = {'date': d.strftime("%d/%m/%Y"), 'slot': random.choice(self.scheduler.slots)}
                    
                # Rebuild slot_subjects and re-allocate
                self._rebuild_allocations()
                
            elif v['type'] in ['invigilator_double_booking', 'invigilator_domain_conflict']:
                # Swap or reassign invigilator
                ds = v['slot']
                self.allocator._assign_invigilators(ds) # Simple re-assignment might fix it if randomized or greedy handles it better
                # Wait, if greedy is deterministic, it will produce the same result.
                # Let's shuffle the available invigilators for this slot and reassign.
                if ds in self.allocator.invigilator_assignments:
                    del self.allocator.invigilator_assignments[ds]
                
                # We can't easily shuffle inside the allocator without modifying it, so we'll just 
                # shuffle the dataframe temporarily
                self.allocator.dl.invigilators_df = self.allocator.dl.invigilators_df.sample(frac=1).reset_index(drop=True)
                self.allocator._assign_invigilators(ds)
                
            elif v['type'] in ['capacity_exceeded', 'one_subject_overfill']:
                # The slot has too many students. Move one subject to a different date/slot.
                ds = v['slot']
                subjects = self.allocator.slot_subjects.get(ds, [])
                if subjects:
                    subject_to_move = random.choice(subjects)
                    d = random.choice(self.scheduler.valid_dates)
                    self.scheduler.schedule[subject_to_move] = {'date': d.strftime("%d/%m/%Y"), 'slot': random.choice(self.scheduler.slots)}
                    self._rebuild_allocations()
                    
            elif v['type'] in ['one_subject_alternation', 'row_alternation', 'seat_uniqueness']:
                # These are purely seating arrangement issues.
                ds = v['slot']
                subjects = self.allocator.slot_subjects.get(ds, [])
                if subjects:
                    random.shuffle(subjects)
                    self.allocator.slot_subjects[ds] = subjects
                    self.allocator._allocate_slot(ds, subjects)
                    self.allocator._assign_invigilators(ds)
                
            elif v['type'] == 'double_booking':
                # Should not happen with sequential filling, but if it does, reallocate
                ds = v['slot']
                subjects = self.allocator.slot_subjects.get(ds, [])
                if subjects:
                    self.allocator._allocate_slot(ds, subjects)
            
            iterations += 1
            violations = self.validator.validate()
            
        return len(violations) == 0

    def _rebuild_allocations(self):
        # Rebuild slot_subjects
        self.allocator.slot_subjects = {}
        for code, info in self.scheduler.schedule.items():
            ds = (info['date'], info['slot'])
            if ds not in self.allocator.slot_subjects:
                self.allocator.slot_subjects[ds] = []
            self.allocator.slot_subjects[ds].append(code)
            
        # Reallocate all
        self.allocator.allocations = {}
        self.allocator.invigilator_assignments = {}
        self.allocator.allocate_all()
