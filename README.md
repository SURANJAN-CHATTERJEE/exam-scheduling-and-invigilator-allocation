# Hybrid AI-Based Exam Scheduling, Duty & Room Allocation System

This project presents an intelligent system for automating university exam scheduling, room allocation, and invigilator assignment using a hybrid AI approach.

## Overview

Exam scheduling is a highly complex combinatorial problem involving multiple constraints such as:
- Student subject clashes
- Room capacity limits
- Faculty availability
- Fair workload distribution

This system combines multiple AI and optimization techniques to generate **conflict-free and optimized schedules automatically**.

---

## Key Features

- Automated exam timetable generation
- Intelligent room allocation with anti-cheating seating logic
- Conflict-free invigilator assignment
- Constraint validation and repair mechanism
- Explainable AI (XAI) using SHAP
- Generation of formatted PDF outputs

---

## Methodology

The system follows a hybrid pipeline:

1. **Genetic Algorithm (GA)**  
   Generates an initial schedule by exploring the search space.

2. **Constraint Satisfaction (CSP)**  
   Validates and repairs constraint violations (hard + soft constraints).

3. **Graph Neural Network (GNN)**  
   Learns and improves scheduling decisions based on feedback.

4. **Explainable AI (SHAP)**  
   Provides interpretation of model decisions.

---

## Dataset

The system uses structured CSV datasets:

- STUDENT DETAILS (PROGRAM, SEMESTER, DEPARTMENT, SPECIALISATION, STUDENT COUNT)
- SUBJECT DETAILS (COURSE_NAME, COURSE_CODE, DEPARTMENT, SEMESTER, SPECIALISATION)
- ROOM DETAILS (Building Number, Room Number, No. of Rows, No. of columns, Total Room Capacity)
- INVIGILATOR DETAILS (EMP_NAME, PREFERED_SUBJECT_CODE)

---

## Output

- Exam Date Sheet (PDF)
- Seating Arrangement (PDF)
- Room Matrix Layout
- Invigilator Duty Allocation
- Utilization Metrics Report

---

## Tech Stack

- Python
- Pandas, NumPy
- DEAP (Genetic Algorithm)
- PyTorch + PyTorch Geometric (GNN)
- SHAP (Explainable AI)
- ReportLab (PDF generation)

---

## Key Highlights

- Ensures **zero scheduling conflicts**
- Optimizes **room utilization**
- Balances **faculty workload**
- Fully automated pipeline

---

## Folder Structure

Project/
   |
   |-----data/
   |      |
   |      |----STUDENT DETAILS.csv
   |      |----SUBJECT DETAILS.csv
   |      |----ROOM DETAILS.csv
   |      |----INVIGILATOR DETAILS.csv
   |
   |-----models/gnn_model.pth
   |
   |-----output/
   |      |
   |      |----date_sheet/Date Sheet for Sem_x {Department}.pdf
   |      |----invigilator/invigilator_duty.pdf
   |      |----room_allotment/room_allotment_metrics.pdf
   |      |----room_metrix/room_sitting_metrix.pdf
   |      |----sitting_arrangement/sitting_arrangement.pdf
   |      |----shap_feature_importence.png
   |
   |-----programs/
   |      |
   |      |----allocatorpy
   |      |----csp_repair.py
   |      |----csp_validator.py
   |      |----data_loader.py
   |      |----evaluator.py
   |      |----gnn_model.py
   |      |----output_generator.py
   |      |----scheduler.py
   |      |----shap_explainer.py
   |
   |----main.py

---

## Note

This project is developed for academic and research purposes.

---

## Future Work

- Replace GA with Reinforcement Learning (PPO)
- Real-time database integration

