class CSPValidator:
    def __init__(self, data_loader, schedule, allocations, invigilators):
        self.dl = data_loader
        self.schedule = schedule
        self.allocations = allocations # (date, slot) -> [room_allocs]
        self.invigilators = invigilators # (date, slot) -> {room: [names]}
        self.violations = []
        
    def validate(self):
        self.violations = []
        self._check_dept_sem_clash()
        self._check_room_constraints()
        self._check_invigilator_constraints()
        self._check_specialization_constraint()
        return self.violations

    def _check_specialization_constraint(self):
        # Ensure no student assigned to wrong subject
        # Ensure all specialization students get their subjects
        for ds, allocs in self.allocations.items():
            for alloc in allocs:
                r_name = f"{alloc['room']['building']}-{alloc['room']['room_no']}"
                for st in alloc['students']:
                    roll = st['roll']
                    sub = st['subject']
                    
                    # Verify this roll is actually supposed to take this subject
                    if roll not in self.dl.subject_students.get(sub, []):
                        self.violations.append({
                            'type': 'specialization_conflict',
                            'slot': ds,
                            'room': r_name,
                            'subject': sub,
                            'roll': roll,
                            'priority': 0 # HARD CONSTRAINT
                        })

    def _check_dept_sem_clash(self):
        # 4. Dept-sem clash
        date_dept_sem = {}
        for code, info in self.schedule.items():
            d = info['date']
            dept = self.dl.subject_details[code]['dept']
            sem = self.dl.subject_details[code]['sem']
            key = (d, dept, sem)
            if key not in date_dept_sem:
                date_dept_sem[key] = []
            date_dept_sem[key].append(code)
            
        for key, codes in date_dept_sem.items():
            if len(codes) > 1:
                self.violations.append({
                    'type': 'dept_sem_clash',
                    'date': key[0],
                    'dept': key[1],
                    'sem': key[2],
                    'codes': codes,
                    'priority': 1
                })

    def _check_room_constraints(self):
        for ds, allocs in self.allocations.items():
            used_rooms = set()
            for alloc in allocs:
                room = alloc['room']
                r_name = f"{room['building']}-{room['room_no']}"
                
                # 6. Double booking
                if r_name in used_rooms:
                    self.violations.append({
                        'type': 'double_booking',
                        'slot': ds,
                        'room': r_name,
                        'priority': 1
                    })
                used_rooms.add(r_name)
                
                students = alloc['students']
                
                # 2. Capacity
                if len(students) > room['cap']:
                    self.violations.append({
                        'type': 'capacity_exceeded',
                        'slot': ds,
                        'room': r_name,
                        'overage': len(students) - room['cap'],
                        'priority': 2
                    })
                    
                # 1. Seat uniqueness
                seats = set()
                for st in students:
                    seat = (st['row'], st['col'])
                    if seat in seats:
                        self.violations.append({
                            'type': 'seat_uniqueness',
                            'slot': ds,
                            'room': r_name,
                            'seat': seat,
                            'priority': 1
                        })
                    seats.add(seat)
                    
                # 7. Seating alternation
                subjects = set(s['subject'] for s in students)
                if len(subjects) == 1:
                    # 1-subject rule: half capacity and alternate columns vacant
                    allowed_cap = room['cap'] // 2
                    if len(students) > allowed_cap:
                        self.violations.append({
                            'type': 'one_subject_overfill',
                            'slot': ds,
                            'room': r_name,
                            'priority': 2
                        })
                    # Check alternate columns
                    used_cols = set(s['col'] for s in students)
                    for col in used_cols:
                        if col % 2 != 0: # Assuming we fill even columns (0, 2, 4...)
                            self.violations.append({
                                'type': 'one_subject_alternation',
                                'slot': ds,
                                'room': r_name,
                                'priority': 3
                            })
                            break
                elif len(subjects) >= 2:
                    # Row-wise alternation: all students in a row should ideally be the same subject
                    # or at least rows should alternate.
                    for r in range(room['rows']):
                        row_subs = set(s['subject'] for s in students if s['row'] == r)
                        if len(row_subs) > 1:
                            self.violations.append({
                                'type': 'row_alternation',
                                'slot': ds,
                                'room': r_name,
                                'row': r,
                                'priority': 3
                            })
                            
    def _check_invigilator_constraints(self):
        # 5. Invigilator conflict
        for ds, room_invigs in self.invigilators.items():
            slot_invigs = set()
            for room, invigs in room_invigs.items():
                for inv in invigs:
                    if inv in slot_invigs:
                        self.violations.append({
                            'type': 'invigilator_double_booking',
                            'slot': ds,
                            'invigilator': inv,
                            'priority': 1
                        })
                    slot_invigs.add(inv)
                    
                # Check domain conflict
                allocs = self.allocations.get(ds, [])
                room_alloc = next((a for a in allocs if f"{a['room']['building']}-{a['room']['room_no']}" == room), None)
                if room_alloc:
                    slot_invigs.add(inv)
