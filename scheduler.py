import datetime
from collections import defaultdict

class Scheduler:
    def __init__(self, data_loader, start_date_str, end_date_str, holidays_str_list):
        self.dl = data_loader
        self.start_date = datetime.datetime.strptime(start_date_str, "%d/%m/%Y").date()
        self.end_date = datetime.datetime.strptime(end_date_str, "%d/%m/%Y").date()
        
        self.holidays = set()
        for h in holidays_str_list:
            if h.strip():
                self.holidays.add(datetime.datetime.strptime(h.strip(), "%d/%m/%Y").date())
                
        self.slots = ["10:00-13:00", "14:00-17:00"]
        self.schedule = {} # code -> {'date': str, 'slot': str}
        self.date_slot_exams = defaultdict(list) # (date, slot) -> [codes]
        self.dept_sem_last_exam = {} # (dept, sem) -> date
        self.valid_dates = self._generate_valid_dates()

    def _generate_valid_dates(self):
        dates = []
        curr = self.start_date
        while curr <= self.end_date:
            if curr.weekday() < 5 and curr not in self.holidays:
                dates.append(curr)
            curr += datetime.timedelta(days=1)
        return dates

    def generate_base_schedule(self):
        # Sort subjects: first by dept, then by sem, then by student count (descending)
        # to schedule larger exams first
        subjects = list(self.dl.subject_students.keys())
        subjects.sort(key=lambda x: (
            self.dl.subject_details[x]['dept'],
            self.dl.subject_details[x]['sem'],
            -len(self.dl.subject_students[x])
        ))

        for code in subjects:
            details = self.dl.subject_details[code]
            dept = details['dept']
            sem = details['sem']
            
            assigned = False
            
            # Start from a random index or a rolling index to distribute
            # Actually, just shuffle the dates to distribute exams naturally
            import random
            shuffled_dates = list(self.valid_dates)
            random.shuffle(shuffled_dates)
            
            for d in shuffled_dates:
                # Check 2-3 day gap constraint for the same dept+sem cohort
                last_exam_date = self.dept_sem_last_exam.get((dept, sem))
                if last_exam_date:
                    gap = abs((d - last_exam_date).days)
                    if gap < 2:
                        continue # Need at least 2 days gap

                if last_exam_date == d:
                    continue

                for slot in self.slots:
                    self.schedule[code] = {'date': d.strftime("%d/%m/%Y"), 'slot': slot}
                    self.date_slot_exams[(d.strftime("%d/%m/%Y"), slot)].append(code)
                    self.dept_sem_last_exam[(dept, sem)] = d
                    assigned = True
                    break
                if assigned:
                    break
                    
            if not assigned:
                print(f"Warning: Could not schedule subject {code} within the given date range.")
                
        return self.schedule
