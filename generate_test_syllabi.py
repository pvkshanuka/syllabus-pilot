"""Generates test syllabus documents: Complete PDF, PDF with missing data (TBA), and high-resolution JPG image."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_syllabi")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_complete_pdf():
    """Generates a complete, multi-assessment university syllabus PDF."""
    pdf_path = os.path.join(OUTPUT_DIR, "complete_cs101_syllabus.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CourseTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "SecHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f766e"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
    )

    story = [
        Paragraph("CS101: Foundations of Computer Science", title_style),
        Paragraph("<b>Academic Term:</b> Fall 2026 &nbsp;|&nbsp; <b>Instructor:</b> Dr. Eleanor Vance &nbsp;|&nbsp; <b>Dates:</b> Sep 07 - Dec 18, 2026", subtitle_style),
        Spacer(1, 8),
        Paragraph("Course Overview", heading_style),
        Paragraph(
            "This course provides a rigorous introduction to computational thinking, algorithms, and data structures. "
            "Students will master control flow, functions, modular architecture, recursion, and object-oriented design.",
            body_style,
        ),
        Spacer(1, 8),
        Paragraph("Grading Breakdown & Assessment Schedule", heading_style),
    ]

    table_data = [
        ["Assessment Name", "Type", "Due Date", "Weight", "Topics Covered"],
        ["Assignment 1: Logic & Flow", "Assignment", "2026-09-25", "10%", "Variables, Loops, Functions"],
        ["Assignment 2: Collections", "Assignment", "2026-10-09", "10%", "Lists, Dictionaries, Sets"],
        ["Midterm Examination 1", "Midterm", "2026-10-15", "15%", "Recursion, Complexity, Flow"],
        ["Assignment 3: OOP Architecture", "Assignment", "2026-11-06", "10%", "Classes, Inheritance, Mixins"],
        ["Midterm Examination 2", "Midterm", "2026-11-19", "15%", "Trees, Sorting, Binary Search"],
        ["Capstone Software Project", "Project", "2026-12-04", "15%", "End-to-End System Design"],
        ["Final Comprehensive Examination", "Final", "2026-12-16", "25%", "Comprehensive All Modules"],
    ]

    t = Table(table_data, colWidths=[160, 75, 75, 55, 160])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 0), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Weekly Modules & Syllabus Topics", heading_style))
    modules = [
        "Week 1-2: Primitive Types, Expressions, Functions & Branching",
        "Week 3-4: Strings, Lists, Dictionaries, and File I/O",
        "Week 5-6: Algorithmic Complexity (Big-O) and Recursion",
        "Week 7-8: Object-Oriented Programming (Classes, Inheritance, Encapsulation)",
        "Week 9-10: Elementary Data Structures (Stacks, Queues, Linked Lists, Trees)",
        "Week 11-12: Searching and Sorting (QuickSort, MergeSort, Binary Search)",
        "Week 13-14: Software Engineering Principles and Capstone Project Integration",
        "Week 15: Final Review & Exam Preparation",
    ]
    for m in modules:
        story.append(Paragraph(f"&bull; {m}", body_style))
        story.append(Spacer(1, 2))

    doc.build(story)
    print(f"Generated: {pdf_path}")


def generate_missing_data_pdf():
    """Generates a syllabus PDF with missing information (TBA dates and weights)."""
    pdf_path = os.path.join(OUTPUT_DIR, "syllabus_missing_dates_tba.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CourseTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#991b1b"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "SecHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#c2410c"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
    )

    story = [
        Paragraph("SE302: Advanced Software Architecture", title_style),
        Paragraph("<b>Term:</b> Fall 2026 &nbsp;|&nbsp; <b>Professor:</b> Dr. Robert Hayes &nbsp;|&nbsp; <b>Dates:</b> Sep 15 - Dec 20, 2026", subtitle_style),
        Spacer(1, 8),
        Paragraph("Important Note on Assessment Dates", heading_style),
        Paragraph(
            "<b>NOTICE FOR STUDENTS:</b> Several examination dates and team milestone deadlines are currently <b>TBA</b> "
            "pending university room scheduling committee approval. Please verify dates once announced.",
            body_style,
        ),
        Spacer(1, 8),
        Paragraph("Assessment Schedule (With Pending / TBA Items)", heading_style),
    ]

    table_data = [
        ["Assessment Name", "Type", "Due Date", "Weight", "Status / Notes"],
        ["Assignment 1: Microservices Design", "Assignment", "2026-10-02", "15%", "Confirmed"],
        ["Midterm Exam (In-Class)", "Midterm", "TBA", "20%", "Room scheduling pending (TBA)"],
        ["Group Project Milestone 1", "Project", "2026-11-10", "15%", "Confirmed"],
        ["Group Project Milestone 2", "Project", "TBA", "15%", "Date to be announced"],
        ["Research Presentation", "Presentation", "2026-12-05", "10%", "Confirmed"],
        ["Final Comprehensive Examination", "Final", "TBA", "25%", "Pending Registrar (TBA)"],
    ]

    t = Table(table_data, colWidths=[160, 75, 75, 55, 160])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991b1b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 0), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fef2f2"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Course Outline", heading_style))
    modules = [
        "Module 1: Monolith to Distributed Systems Decomposition",
        "Module 2: Event-Driven Architecture & Message Brokers",
        "Module 3: Distributed Transactions, Saga Pattern, and CAP Theorem",
        "Module 4: API Gateways, Service Meshes, and Observability",
        "Module 5: Resiliency Patterns (Circuit Breakers, Bulkheads, Retries)",
    ]
    for m in modules:
        story.append(Paragraph(f"&bull; {m}", body_style))
        story.append(Spacer(1, 2))

    doc.build(story)
    print(f"Generated: {pdf_path}")


def generate_jpg_syllabus():
    """Generates a crisp, high-resolution JPG image of a university syllabus."""
    img_path = os.path.join(OUTPUT_DIR, "syllabus_photo_datascience.jpg")
    width = 1200
    height = 1450

    img = Image.new("RGB", (width, height), color="#f8fafc")
    draw = ImageDraw.Draw(img)

    # Use default font or truetype
    try:
        font_large = ImageFont.truetype("arial.ttf", 34)
        font_sub = ImageFont.truetype("arial.ttf", 18)
        font_sec = ImageFont.truetype("arial.ttf", 24)
        font_body = ImageFont.truetype("arial.ttf", 17)
        font_bold = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = font_large
        font_sec = font_large
        font_body = font_large
        font_bold = font_large

    # Header Card
    draw.rectangle([40, 40, width - 40, 170], fill="#0f766e")
    draw.text((70, 60), "DS301: Applied Machine Learning & Data Science", fill="#ffffff", font=font_large)
    draw.text((70, 115), "Fall 2026 | Prof. Marcus Lindqvist | Term: Sep 01 - Dec 15, 2026", fill="#ccfbf1", font=font_sub)

    # Course Overview
    y = 200
    draw.text((50, y), "Course Description & Topics", fill="#0f172a", font=font_sec)
    y += 35
    desc = (
        "This course explores end-to-end data pipelines, supervised regression and classification,\n"
        "ensemble methods (Random Forests, XGBoost), unsupervised clustering, and neural networks.\n"
        "Students build real-world ML projects with rigorous cross-validation and bias evaluation."
    )
    draw.text((50, y), desc, fill="#334155", font=font_body)

    # Table Header
    y += 100
    draw.text((50, y), "Deliverables & Graded Assessments", fill="#0f172a", font=font_sec)
    y += 40

    table_x = 50
    table_w = width - 100
    draw.rectangle([table_x, y, table_x + table_w, y + 45], fill="#1e293b")
    draw.text((table_x + 15, y + 12), "Assessment", fill="#ffffff", font=font_bold)
    draw.text((table_x + 400, y + 12), "Type", fill="#ffffff", font=font_bold)
    draw.text((table_x + 550, y + 12), "Due Date", fill="#ffffff", font=font_bold)
    draw.text((table_x + 720, y + 12), "Weight", fill="#ffffff", font=font_bold)
    draw.text((table_x + 850, y + 12), "Coverage Focus", fill="#ffffff", font=font_bold)

    assessments = [
        ("Quiz 1: Python Data Science Tools", "Quiz", "2026-09-18", "5%", "NumPy & Pandas indexing"),
        ("Lab Project 1: Housing Regression", "Lab", "2026-10-02", "15%", "Feature engineering, RMSE"),
        ("Midterm Written Examination", "Midterm", "2026-10-22", "20%", "Supervised learning theory"),
        ("Lab Project 2: Churn Classification", "Lab", "2026-11-13", "20%", "ROC-AUC & XGBoost tuning"),
        ("Capstone ML Pipeline & Report", "Project", "2026-12-01", "25%", "End-to-End production ML"),
        ("Final Oral Defense & Exam", "Final", "2026-12-11", "15%", "Architecture & Hyperparameters"),
    ]

    y += 45
    for i, (name, a_type, due, wt, focus) in enumerate(assessments):
        bg = "#ffffff" if i % 2 == 0 else "#f1f5f9"
        draw.rectangle([table_x, y, table_x + table_w, y + 45], fill=bg, outline="#e2e8f0")
        draw.text((table_x + 15, y + 12), name, fill="#0f172a", font=font_body)
        draw.text((table_x + 400, y + 12), a_type, fill="#475569", font=font_body)
        draw.text((table_x + 550, y + 12), due, fill="#0f766e", font=font_bold)
        draw.text((table_x + 720, y + 12), wt, fill="#b91c1c", font=font_bold)
        draw.text((table_x + 850, y + 12), focus, fill="#334155", font=font_body)
        y += 45

    # Syllabus Outline
    y += 40
    draw.text((50, y), "Course Outline & Weekly Modules", fill="#0f172a", font=font_sec)
    y += 35
    modules = [
        "Module 1: Exploratory Data Analysis, Pandas, Matplotlib, Data Cleaning",
        "Module 2: Linear Regression, Regularization (Ridge, Lasso), Evaluation Metrics",
        "Module 3: Classification Algorithms (Logistic Regression, Decision Trees)",
        "Module 4: Tree Ensembles (Random Forests, XGBoost, LightGBM)",
        "Module 5: Unsupervised Learning (K-Means Clustering, PCA, Dimensionality Reduction)",
        "Module 6: Neural Networks, PyTorch Basics, Backpropagation",
        "Module 7: Responsible AI, Bias Detection, Model Deployment",
    ]
    for mod in modules:
        draw.text((70, y), f"• {mod}", fill="#334155", font=font_body)
        y += 30

    img.save(img_path, "JPEG", quality=95)
    print(f"Generated: {img_path}")


def generate_text_syllabi():
    """Generates plain text versions of the test syllabi for copy-paste testing."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 1. Complete
    complete_txt_path = os.path.join(OUTPUT_DIR, "complete_cs101_syllabus.txt")
    sample_src = os.path.join(base_dir, "samples", "sample_cs101_syllabus.txt")
    with open(sample_src, "r", encoding="utf-8") as src, open(complete_txt_path, "w", encoding="utf-8") as dst:
        dst.write(src.read())

    # 2. Missing TBA
    missing_txt_path = os.path.join(OUTPUT_DIR, "syllabus_missing_dates_tba.txt")
    missing_content = """COURSE SYLLABUS: SE302 Advanced Software Architecture
Academic Year: Fall 2026
Instructor: Dr. Robert Hayes (rhayes@university.edu)
Semester Dates: September 15, 2026 to December 20, 2026

Course Modules:
- Module 1: Monolith to Distributed Systems Decomposition
- Module 2: Event-Driven Architecture & Message Brokers
- Module 3: Distributed Transactions, Saga Pattern, and CAP Theorem
- Module 4: API Gateways, Service Meshes, and Observability
- Module 5: Resiliency Patterns (Circuit Breakers, Bulkheads, Retries)

Grading Breakdown & Assessment Schedule:
1. Assignment 1: Microservices Design
   - Due Date: 2026-10-02
   - Weight: 15%
   - Description: Architecture proposal and boundary context mapping.

2. Midterm Exam (In-Class)
   - Due Date: TBA
   - Weight: 20%
   - Description: Written examination on Modules 1-3. Date pending room scheduling (TBA).

3. Group Project Milestone 1
   - Due Date: 2026-11-10
   - Weight: 15%
   - Description: Core event broker implementation.

4. Group Project Milestone 2
   - Due Date: TBA
   - Weight: 15%
   - Description: Observability dashboard and resilience testing (Date TBA).

5. Research Presentation
   - Due Date: 2026-12-05
   - Weight: 10%
   - Description: 15-minute presentation on modern distributed systems papers.

6. Final Comprehensive Examination
   - Due Date: TBA
   - Weight: 25%
   - Description: Final examination scheduled during official exam period (TBA).
"""
    with open(missing_txt_path, "w", encoding="utf-8") as f:
        f.write(missing_content)

    print("Generated text syllabi.")


if __name__ == "__main__":
    generate_complete_pdf()
    generate_missing_data_pdf()
    generate_jpg_syllabus()
    generate_text_syllabi()
    print("All test syllabi generated successfully in test_syllabi/")
