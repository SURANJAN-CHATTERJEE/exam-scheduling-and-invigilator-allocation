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

- Student data (program, semester, count)
- Subject data (core/specialization)
- Room data (capacity, layout)
- Invigilator data (availability & preferences)

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

## Note

This project is developed for academic and research purposes.

---

## Future Work

- Replace GA with Reinforcement Learning (PPO)
- Real-time database integration

