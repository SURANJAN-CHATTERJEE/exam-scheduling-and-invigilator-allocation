import pandas as pd
import os
import math
import re

class DataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.students_df = None
        self.subjects_df = None
        self.rooms_df = None
        self.invigilators_df = None
        
        self.student_cohorts = {} # (program, dept, sem, spec) -> list of ids
        self.subject_students = {} # subject_code -> list of ids
        self.subject_details = {} # subject_code -> dict of details
        
    def load_all(self):
        print("Loading CSV files...")
        self.students_df = pd.read_csv(os.path.join(self.data_dir, "STUDENT DETAILS.csv"))
        self.subjects_df = pd.read_csv(os.path.join(self.data_dir, "SUBJECT DETAILS.csv"))
        self.rooms_df = pd.read_csv(os.path.join(self.data_dir, "ROOMS DETAILS.csv"))
        self.invigilators_df = pd.read_csv(os.path.join(self.data_dir, "INVIGILATOR DETAILS.csv"))
        
        # Clean up column names (strip whitespace)
        self.students_df.columns = self.students_df.columns.str.strip()
        self.subjects_df.columns = self.subjects_df.columns.str.strip()
        self.rooms_df.columns = self.rooms_df.columns.str.strip()
        self.invigilators_df.columns = self.invigilators_df.columns.str.strip()

        # Clean string values
        for df in [self.students_df, self.subjects_df, self.rooms_df, self.invigilators_df]:
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()

        # Generate IDs and map subjects
        self._generate_student_ids()
        self._build_subject_map()
        
        print("Data loaded successfully.")
        
    def _generate_student_ids(self):
        counters = {}
        for idx, row in self.students_df.iterrows():
            program = str(row['PROGRAM']).strip()
            dept = str(row['DEPARTMENT']).strip()
            sem = str(row['SEMESTER']).strip()
            spec = str(row['SPECIALISATION']).strip()
            count = int(row['STUDENT COUNT'])
            
            key = f"{program}_{dept}"
            if key not in counters:
                counters[key] = 1
                
            cohort_ids = []
            for _ in range(count):
                roll = f"{program}/{dept}/{counters[key]:04d}"
                cohort_ids.append(roll)
                counters[key] += 1
                
            self.student_cohorts[(program, dept, sem, spec)] = cohort_ids
            
    def _build_subject_map(self):
        # First group subjects by dept and sem to find electives
        electives_by_dept_sem = {}
        for idx, row in self.subjects_df.iterrows():
            dept = str(row['DEPARTMENT']).strip()
            sem = str(row['SEMESTER']).strip()
            spec = str(row['SPECIALISATION']).strip()
            code = str(row['COURSE_CODE']).strip()
            
            self.subject_details[code] = {
                'name': row['COURSE_NAME'],
                'dept': dept,
                'sem': sem,
                'spec': spec
            }
            
            if spec == 'ELECTIVE':
                if (dept, sem) not in electives_by_dept_sem:
                    electives_by_dept_sem[(dept, sem)] = []
                electives_by_dept_sem[(dept, sem)].append(code)
                
        # Now map students to subjects using STRICT SPECIALIZATION LOGIC
        for idx, row in self.subjects_df.iterrows():
            code = str(row['COURSE_CODE']).strip()
            if code == 'nan' or code == 'NULL':
                continue # Skip NULL subjects (like experiential learning)
                
            dept = str(row['DEPARTMENT']).strip()
            sem = str(row['SEMESTER']).strip()
            spec = str(row['SPECIALISATION']).strip()
            
            assigned_students = []
            
            # IF subject_type == CORE: (spec == 'ALL')
            if spec == 'ALL':
                for (c_prog, c_dept, c_sem, c_spec), st_list in self.student_cohorts.items():
                    if c_dept == dept and c_sem == sem:
                        # ALL students of that dept+sem
                        assigned_students.extend(st_list)
            
            # ELSE (Specialization or Elective):
            else:
                for (c_prog, c_dept, c_sem, c_spec), st_list in self.student_cohorts.items():
                    if c_dept == dept and c_sem == sem:
                        if spec == 'ELECTIVE' and c_spec == 'ALL':
                            # Handle electives similarly as before (divide core students among electives)
                            electives = electives_by_dept_sem.get((dept, sem), [])
                            if electives:
                                e_idx = electives.index(code)
                                chunk_size = math.ceil(len(st_list) / len(electives))
                                start = e_idx * chunk_size
                                end = start + chunk_size
                                assigned_students.extend(st_list[start:end])
                        elif c_spec == spec:
                            # Strict match: group.specialization == subject.specialization
                            assigned_students.extend(st_list)
                            
            if assigned_students:
                self.subject_students[code] = assigned_students
                
if __name__ == "__main__":
    dl = DataLoader("data")
    dl.load_all()
    print(f"Loaded {len(dl.subject_students)} valid subjects with mapped students.")
