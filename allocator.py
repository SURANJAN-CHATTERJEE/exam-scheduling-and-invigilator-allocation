import math

class Allocator:
    def __init__(self, data_loader, schedule):
        self.dl = data_loader
        self.schedule = schedule # code -> {'date': str, 'slot': str}
        # Reverse schedule mapping: (date, slot) -> [codes]
        self.slot_subjects = {}
        for code, info in schedule.items():
            ds = (info['date'], info['slot'])
            if ds not in self.slot_subjects:
                self.slot_subjects[ds] = []
            self.slot_subjects[ds].append(code)
            
        self.allocations = {} # (date, slot) -> list of room allocations
        self.invigilator_assignments = {} # (date, slot) -> {room: [invigilators]}
        
    def allocate_all(self):
        for ds, subjects in self.slot_subjects.items():
            self._allocate_slot(ds, subjects)
            self._assign_invigilators(ds)

    def _allocate_slot(self, ds, subjects):
        # Gather all students needed to be seated
        student_queues = {}
        for sub in subjects:
            student_queues[sub] = list(self.dl.subject_students[sub])
            
        # Get list of rooms sorted sequentially (e.g. B1, B2)
        rooms = []
        for idx, r in self.dl.rooms_df.iterrows():
            rooms.append({
                'building': str(r['Building Number']).strip(),
                'room_no': str(r['Room Number']).strip(),
                'rows': int(r['No. of Rows']),
                'cols': int(r['No. of columns']),
                'cap': int(r['Total Room Capacity'])
            })
            
        room_allocs = []
        
        # While there are students left to be seated
        active_subjects = [sub for sub in student_queues if len(student_queues[sub]) > 0]
        
        for room in rooms:
            if not active_subjects:
                break
                
            r_rows = room['rows']
            r_cols = room['cols']
            
            # Decide subjects for this room
            # Prefer 2 subjects to alternate rows
            room_subjects = []
            if len(active_subjects) >= 2:
                # Pick top 2 subjects with most students
                active_subjects.sort(key=lambda x: len(student_queues[x]), reverse=True)
                room_subjects = active_subjects[:2]
            else:
                room_subjects = [active_subjects[0]]

            seating_grid = [[None for _ in range(r_cols)] for _ in range(r_rows)]
            placed_students = []
            
            if len(room_subjects) >= 2:
                # Fill COLUMN-WISE, Alternate ROW-WISE
                # For 2 subjects, R1=sub1, R2=sub2, R3=sub1...
                for c in range(r_cols):
                    for r in range(r_rows):
                        sub_idx = r % len(room_subjects)
                        sub = room_subjects[sub_idx]
                        if student_queues[sub]:
                            st = student_queues[sub].pop(0)
                            seating_grid[r][c] = {'subject': sub, 'roll': st}
                            placed_students.append({'subject': sub, 'roll': st, 'row': r, 'col': c})
            else:
                # Only 1 subject available. Rule: allocate (capacity/2), alternate columns vacant.
                sub = room_subjects[0]
                allowed_cap = room['cap'] // 2
                placed_count = 0
                for c in range(0, r_cols, 2): # Alternate columns
                    for r in range(r_rows):
                        if student_queues[sub] and placed_count < allowed_cap:
                            st = student_queues[sub].pop(0)
                            seating_grid[r][c] = {'subject': sub, 'roll': st}
                            placed_students.append({'subject': sub, 'roll': st, 'row': r, 'col': c})
                            placed_count += 1
            
            if placed_students:
                room_allocs.append({
                    'room': room,
                    'seating': seating_grid,
                    'students': placed_students
                })
                
            active_subjects = [sub for sub in student_queues if len(student_queues[sub]) > 0]
            
        if active_subjects:
            print(f"Warning: Not enough rooms for slot {ds}. Unseated students remain.")
            
        self.allocations[ds] = room_allocs

    def _assign_invigilators(self, ds):
        room_allocs = self.allocations.get(ds, [])
        if not room_allocs:
            return
            
        invig_df = self.dl.invigilators_df
        available = []
        for idx, row in invig_df.iterrows():
            available.append({
                'name': row['EMP_NAME'],
                'domains': [x.strip() for x in str(row['PREFERED_SUBJECT_CODE']).split(',')]
            })
            
        assignments = {}
        # Simple greedy assignment
        # Phase 5 (CSP repair) can swap them if conflicts exist
        for alloc in room_allocs:
            room_name = alloc['room']['building'] + "-" + alloc['room']['room_no']
            cap = len(alloc['students'])
            req_count = 2 if alloc['room']['cap'] <= 50 else 3
            
            room_subjects = list(set(s['subject'] for s in alloc['students']))
            
            assigned = []
            for inv in list(available):
                if len(assigned) == req_count:
                    break
                
                # Cannot invigilate own subject
                conflict = False
                for sub in room_subjects:
                    if sub in inv['domains'] and 'ALL' not in inv['domains']:
                        conflict = True
                        break
                
                if not conflict:
                    assigned.append(inv)
                    available.remove(inv)
                    
            # If we couldn't find enough non-conflicting, just assign anyone to meet count (CSP will repair)
            while len(assigned) < req_count and available:
                assigned.append(available.pop(0))
                
            assignments[room_name] = [x['name'] for x in assigned]
            
        self.invigilator_assignments[ds] = assignments
