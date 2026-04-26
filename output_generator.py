import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd

class OutputGenerator:
    def __init__(self, scheduler, allocator, out_dir="output"):
        self.scheduler = scheduler
        self.allocator = allocator
        self.out_dir = out_dir
        
        self.dirs = {
            'date_sheet': os.path.join(self.out_dir, "date_sheet"),
            'sitting_arrangement': os.path.join(self.out_dir, "sitting_arrangement"),
            'room_allotment': os.path.join(self.out_dir, "room_allotment"),
            'room_matrix': os.path.join(self.out_dir, "room_matrix"),
            'invigilator': os.path.join(self.out_dir, "invigilator")
        }
        
        for d in self.dirs.values():
            if not os.path.exists(d):
                os.makedirs(d)
                
        self.styles = getSampleStyleSheet()

    def generate_all(self):
        print("Generating PDFs...")
        self._generate_date_sheets()
        self._generate_master_seating()
        self._generate_room_matrix()
        self._generate_invigilator_duty()
        self._generate_room_allotment_metrics()
        print("PDFs generated in /output/")

    def _generate_date_sheets(self):
        # Group by Dept and Sem
        dept_sem_schedule = {}
        for code, info in self.scheduler.schedule.items():
            details = self.scheduler.dl.subject_details[code]
            dept = details['dept']
            sem = details['sem']
            key = (dept, sem)
            if key not in dept_sem_schedule:
                dept_sem_schedule[key] = []
            dept_sem_schedule[key].append({
                'Date': info['date'],
                'Slot': info['slot'],
                'Course Code': code,
                'Course Name': details['name']
            })
            
        for (dept, sem), exams in dept_sem_schedule.items():
            # Sort exams by date
            exams.sort(key=lambda x: pd.to_datetime(x['Date'], format='%d/%m/%Y'))
            
            file_path = os.path.join(self.dirs['date_sheet'], f"Date Sheet for Sem_{sem} {dept}.pdf")
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            elements = []
            elements.append(Paragraph(f"Date Sheet for Semester {sem} - {dept}", self.styles['Title']))
            elements.append(Spacer(1, 20))
            
            data = [["Sl No", "Department", "Semester", "Date", "Slot", "Course Code", "Course Name"]]
            for i, ex in enumerate(exams):
                data.append([str(i+1), dept, sem, ex['Date'], ex['Slot'], ex['Course Code'], ex['Course Name']])
                
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t)
            doc.build(elements)

    def _generate_master_seating(self):
        file_path = os.path.join(self.dirs['sitting_arrangement'], "sitting_arrangement.pdf")
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        
        for ds, allocs in self.allocator.allocations.items():
            if not allocs: continue
            
            elements.append(Paragraph(f"Master Seating Arrangement: {ds[0]} | Slot: {ds[1]}", self.styles['Title']))
            elements.append(Spacer(1, 20))
            
            data = [["Room No", "Capacity", "Roll Numbers"]]
            
            for alloc in allocs:
                room_no = f"{alloc['room']['building']}-{alloc['room']['room_no']}"
                cap = str(alloc['room']['cap'])
                
                # Group students by cohort
                cohorts = {}
                for st in alloc['students']:
                    code = st['subject']
                    dept = self.scheduler.dl.subject_details[code]['dept']
                    sem = self.scheduler.dl.subject_details[code]['sem']
                    prog = st['roll'].split('/')[0]
                    key = f"{prog} :: {dept} :: Sem-{sem} ::"
                    if key not in cohorts:
                        cohorts[key] = []
                    cohorts[key].append(st['roll'])
                    
                rolls_text = ""
                for k, rolls in cohorts.items():
                    rolls_text += f"{k}\n{';'.join(rolls)}\n[TOTAL COUNT={len(rolls)}]\n\n"
                    
                data.append([room_no, cap, Paragraph(rolls_text.replace('\n', '<br/>'), self.styles['Normal'])])
                
            t = Table(data, colWidths=[80, 60, 350])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t)
            elements.append(PageBreak())
            
        if elements:
            doc.build(elements)

    def _generate_room_matrix(self):
        file_path = os.path.join(self.dirs['room_matrix'], "room_seating_matrix.pdf")
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        
        # Main Title
        title_style = self.styles['Title']
        title_style.fontSize = 18
        elements.append(Paragraph("<b>Room Seating Matrix</b>", title_style))
        elements.append(Spacer(1, 10))
        
        subtitle_style = self.styles['Normal']
        subtitle_style.fontSize = 9
        elements.append(Paragraph("OUTPUT TYPE 4 — Phase 2 Formatted Output", subtitle_style))
        elements.append(Spacer(1, 30))
        
        for ds, allocs in self.allocator.allocations.items():
            if not allocs: continue
            
            date_str = ds[0].replace('/', '-')
            shift_str = ds[1].replace(':', '')
            
            for alloc in allocs:
                room_no = f"{alloc['room']['building']}-{alloc['room']['room_no']}"
                
                # Room Subtitle
                room_title_style = self.styles['Heading3']
                room_title = f"<i><b>Room: {room_no} | Date: {ds[0].replace('/', '-')} | Session: {ds[1].replace(':', '')}</b></i>"
                elements.append(Paragraph(room_title, room_title_style))
                elements.append(Spacer(1, 10))
                
                cols = alloc['room']['cols']
                rows = alloc['room']['rows']
                
                # Initialize transposed grid to show column-wise alternation
                grid = [["" for _ in range(rows)] for _ in range(cols)]
                
                # Populate grid with subject codes (transposed)
                for st in alloc['students']:
                    r = st['row']
                    c = st['col']
                    grid[c][r] = st['subject']
                    
                # Prepare table data (headers are now based on original rows)
                header = [f"Col {r+1}" for r in range(rows)]
                data = [header] + grid
                
                # Calculate column width to fit page
                available_width = letter[0] - 2 * 36 # 1 inch margins (approx 72 pts total)
                col_width = available_width / rows if rows > 0 else 50
                
                t = Table(data, colWidths=[col_width] * rows)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                ]))
                
                elements.append(t)
                elements.append(PageBreak())
                
        doc.build(elements)

    def _generate_invigilator_duty(self):
        file_path = os.path.join(self.dirs['invigilator'], "invigilator_duty.pdf")
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        elements.append(Paragraph("Master Invigilator Duty List", self.styles['Title']))
        elements.append(Spacer(1, 20))
        
        data = [["Name", "Date", "Shift", "Room"]]
        
        for ds, rooms in self.allocator.invigilator_assignments.items():
            date_str = ds[0]
            shift_str = ds[1]
            for room, invigs in rooms.items():
                for inv in invigs:
                    data.append([inv, date_str, shift_str, room])
                    
        # Sort by Name, then Date
        data[1:] = sorted(data[1:], key=lambda x: (x[0], x[1]))
        
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)
        doc.build(elements)

    def _generate_room_allotment_metrics(self):
        print("[INFO] Saving room allotment metrics...")
        file_path = os.path.join(self.dirs['room_allotment'], "room_allotment_metrics.pdf")
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        
        for ds, allocs in self.allocator.allocations.items():
            if not allocs: continue
            
            elements.append(Paragraph(f"Room Allotment Metrics: {ds[0]} | Shift: {ds[1]}", self.styles['Title']))
            elements.append(Spacer(1, 20))
            
            data = [["Room No", "Capacity", "Students\nAssigned", "Utilization", "No. of\nSubjects", "Subject Mix", "Empty\nSeats"]]
            
            total_rooms = 0
            total_students = 0
            fully_utilized = 0
            empty_rooms_count = 0
            total_utilization_sum = 0
            
            for alloc in allocs:
                room_no = f"{alloc['room']['building']}-{alloc['room']['room_no']}"
                cap = alloc['room']['cap']
                assigned = len(alloc['students'])
                
                # Validation before metrics
                if assigned > cap:
                    print(f"WARNING: students_assigned ({assigned}) > capacity ({cap}) in room {room_no}")
                if assigned > 0 and assigned == 0: # This logically can't happen based on rules, but adding assertion constraint conceptually
                    pass
                    
                utilization = (assigned / cap) * 100 if cap > 0 else 0
                empty_seats = cap - assigned
                subjects_set = set(st['subject'] for st in alloc['students'])
                num_subjects = len(subjects_set)
                subject_mix = ", ".join(list(subjects_set))
                
                # Wrapping long subject lists for reportlab table via Paragraph
                subject_mix_p = Paragraph(subject_mix, self.styles['Normal'])
                
                data.append([
                    room_no, str(cap), str(assigned), f"{utilization:.1f}%", 
                    str(num_subjects), subject_mix_p, str(empty_seats)
                ])
                
                total_rooms += 1
                total_students += assigned
                total_utilization_sum += utilization
                if empty_seats == 0 and assigned > 0:
                    fully_utilized += 1
                if assigned == 0:
                    empty_rooms_count += 1
                    print(f"WARNING: empty room {room_no} exists but students exist in allocation.")
                    
            avg_utilization = total_utilization_sum / total_rooms if total_rooms > 0 else 0
            
            # Using smaller font if needed is handled by setting table font size or colWidths
            t = Table(data, colWidths=[80, 50, 60, 60, 60, 160, 50])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9), # Use smaller font
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 30))
            
            # Aggregated Metrics Summary
            summary_style = self.styles['Normal']
            summary_style.fontSize = 11
            
            summary_text = f"""
            <b>AGGREGATED METRICS</b><br/>
            Total Rooms Used: {total_rooms}<br/>
            Total Students Assigned: {total_students}<br/>
            Average Utilization: {avg_utilization:.2f}%<br/>
            Empty Rooms Count: {empty_rooms_count}<br/>
            Fully Utilized Rooms: {fully_utilized}
            """
            elements.append(Paragraph(summary_text, summary_style))
            elements.append(PageBreak())
            
        if elements:
            doc.build(elements)
            
        print("[INFO] Output saved to output/room_allotment/")
