# -*- coding: utf-8 -*-
import os
import re
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent=" ")

def cdata(text):
    """Wrap text in CDATA if not empty."""
    if text is None:
        return ""
    return f"<![CDATA[{text}]]>"

def normalize_question_text(fields):
    """Join LimeSurvey fields into readable question text."""
    return " ".join(f"{f.get('name', '')} {f.get('value', '')}" for f in fields)

def load_explanation(q_path):
    """Load feedback/explanation text if available."""
    exp_file = os.path.join(q_path, "explanation.json")
    if os.path.exists(exp_file):
        with open(exp_file, "r", encoding="utf-8") as f:
            return json.load(f).get("text", "")
    return ""

def group_question_folders(lesson_dir):
    """Group folders (e.g., 3a, 3b) into single questions, sorted numerically."""
    grouped = {}
    for entry in os.listdir(lesson_dir):
        if not os.path.isdir(os.path.join(lesson_dir, entry)):
            continue
        m = re.match(r"(\d+)([a-z]*)", entry, re.I)
        if m:
            num = int(m.group(1))
            suffix = m.group(2).lower()
            grouped.setdefault(num, []).append((suffix, entry))
    # Sort by number, then by suffix
    sorted_grouped = {}
    for num in sorted(grouped.keys()):
        sorted_grouped[num] = [e for _, e in sorted(grouped[num])]
    return sorted_grouped

def load_lesson_data(lesson_dir, lesson_name, lesson_number):
    """Load all questions from a lesson directory."""
    questions = []
    groups = group_question_folders(lesson_dir)
    qid = 1
    for num, entries in groups.items():
        q_code = f"L{lesson_number}Q{qid}"
        if len(entries) > 1:  # multiple short text
            subqs = []
            for idx, e in enumerate(entries, start=1):
                q_path = os.path.join(lesson_dir, e)
                with open(os.path.join(q_path, "question.json"), "r", encoding="utf-8") as f:
                    data = json.load(f)
                subqs.append({
                    "code": f"{q_code}_SQ{idx}",
                    "text": normalize_question_text(data.get("fields", [])),
                    "answers": data.get("answers", [])
                })
            questions.append({
                "qid": qid,
                "type": "Q",  # multiple short text
                "title": q_code,
                "question": f"Lesson {lesson_number} Question {num}",
                "subquestions": subqs,
                "feedback": load_explanation(os.path.join(lesson_dir, entries[0]))
            })
        else:  # single question
            q_path = os.path.join(lesson_dir, entries[0])
            with open(os.path.join(q_path, "question.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            q_type = data.get("type", "Open")
            if q_type == "Checkbox":
                ltype = "L"  # List (radio)
            else:
                ltype = "S"  # Short free text
            questions.append({
                "qid": qid,
                "type": ltype,
                "title": q_code,
                "question": normalize_question_text(data.get("fields", [])),
                "answers": data.get("answers", []),
                "feedback": load_explanation(q_path)
            })
        qid += 1
    return {"group_name": lesson_name, "questions": questions}

def build_lsg_xml(lesson_data, sid=999999, gid=2, group_order=2):
    """Build LimeSurvey .lsg XML structure from lesson data."""
    doc = ET.Element("document")
    ET.SubElement(doc, "LimeSurveyDocType").text = "Group"
    ET.SubElement(doc, "DBVersion").text = "636"

    langs = ET.SubElement(doc, "languages")
    ET.SubElement(langs, "language").text = "en"

    # Groups
    groups = ET.SubElement(doc, "groups")
    fields = ET.SubElement(groups, "fields")
    for name in ["gid", "sid", "group_order", "randomization_group", "grelevance"]:
        ET.SubElement(fields, "fieldname").text = name
    rows = ET.SubElement(groups, "rows")
    row = ET.SubElement(rows, "row")
    ET.SubElement(row, "gid").text = str(gid)
    ET.SubElement(row, "sid").text = str(sid)
    ET.SubElement(row, "group_order").text = str(group_order)
    ET.SubElement(row, "randomization_group")
    ET.SubElement(row, "grelevance").text = "1"

    # Group l10ns
    group_l10ns = ET.SubElement(doc, "group_l10ns")
    fields = ET.SubElement(group_l10ns, "fields")
    for name in ["id", "gid", "group_name", "description", "language", "sid", "group_order", "randomization_group", "grelevance"]:
        ET.SubElement(fields, "fieldname").text = name
    rows = ET.SubElement(group_l10ns, "rows")
    row = ET.SubElement(rows, "row")
    ET.SubElement(row, "id").text = str(gid)
    ET.SubElement(row, "gid").text = str(gid)
    ET.SubElement(row, "group_name").text = lesson_data["group_name"]
    ET.SubElement(row, "description")
    ET.SubElement(row, "language").text = "en"
    ET.SubElement(row, "sid").text = str(sid)
    ET.SubElement(row, "group_order").text = str(group_order)
    ET.SubElement(row, "randomization_group")
    ET.SubElement(row, "grelevance").text = "1"

    # Questions
    questions = ET.SubElement(doc, "questions")
    fields = ET.SubElement(questions, "fields")
    for name in ["qid", "parent_qid", "sid", "gid", "type", "title", "question_order", "relevance", "mandatory"]:
        ET.SubElement(fields, "fieldname").text = name
    rows = ET.SubElement(questions, "rows")

    # Question l10ns
    ql10ns = ET.SubElement(doc, "question_l10ns")
    fields = ET.SubElement(ql10ns, "fields")
    for name in ["id", "qid", "question", "language"]:
        ET.SubElement(fields, "fieldname").text = name
    ql10n_rows = ET.SubElement(ql10ns, "rows")

    # Answers
    answers = ET.SubElement(doc, "answers")
    fields = ET.SubElement(answers, "fields")
    for name in ["aid", "qid", "code", "assessment_value", "scale_id", "sortorder"]:
        ET.SubElement(fields, "fieldname").text = name
    answer_rows = ET.SubElement(answers, "rows")

    answer_l10ns = ET.SubElement(doc, "answer_l10ns")
    fields = ET.SubElement(answer_l10ns, "fields")
    for name in ["id", "aid", "qid", "answer", "language"]:
        ET.SubElement(fields, "fieldname").text = name
    answer_l10n_rows = ET.SubElement(answer_l10ns, "rows")

    # Subquestions
    subqs = ET.SubElement(doc, "subquestions")
    fields = ET.SubElement(subqs, "fields")
    for name in ["qid", "parent_qid", "sid", "gid", "type", "title", "question_order", "scale_id"]:
        ET.SubElement(fields, "fieldname").text = name
    subq_rows = ET.SubElement(subqs, "rows")

    subq_l10ns = ET.SubElement(doc, "subquestion_l10ns")
    fields = ET.SubElement(subq_l10ns, "fields")
    for name in ["id", "qid", "question", "language"]:
        ET.SubElement(fields, "fieldname").text = name
    subq_l10n_rows = ET.SubElement(subq_l10ns, "rows")

    # Question attributes
    q_attrs = ET.SubElement(doc, "question_attributes")
    fields = ET.SubElement(q_attrs, "fields")
    for name in ["qid", "attribute", "value", "language"]:
        ET.SubElement(fields, "fieldname").text = name
    q_attr_rows = ET.SubElement(q_attrs, "rows")

    q_order = 1
    aid = 1
    subq_id = 1000

    for q in lesson_data["questions"]:
        # Question row
        row = ET.SubElement(rows, "row")
        ET.SubElement(row, "qid").text = str(q["qid"])
        ET.SubElement(row, "parent_qid").text = "0"
        ET.SubElement(row, "sid").text = str(sid)
        ET.SubElement(row, "gid").text = str(gid)
        ET.SubElement(row, "type").text = q["type"]
        ET.SubElement(row, "title").text = q["title"]
        ET.SubElement(row, "question_order").text = str(q_order)
        ET.SubElement(row, "relevance").text = "1"
        ET.SubElement(row, "mandatory").text = "S"  # Soft mandatory

        # Question translation
        row_l10n = ET.SubElement(ql10n_rows, "row")
        ET.SubElement(row_l10n, "id").text = str(q["qid"])
        ET.SubElement(row_l10n, "qid").text = str(q["qid"])
        ET.SubElement(row_l10n, "question").text = q["question"]
        ET.SubElement(row_l10n, "language").text = "en"

        # Checkbox → Radio List answers
        if q["type"] == "L":
            for code, text in [("Y", "Yes I agree"), ("N", "No I disagree")]:
                arow = ET.SubElement(answer_rows, "row")
                ET.SubElement(arow, "aid").text = str(aid)
                ET.SubElement(arow, "qid").text = str(q["qid"])
                ET.SubElement(arow, "code").text = code
                ET.SubElement(arow, "assessment_value").text = "1" if code == "Y" else "0"
                ET.SubElement(arow, "scale_id").text = "0"
                ET.SubElement(arow, "sortorder").text = "1" if code == "Y" else "2"

                l10n_row = ET.SubElement(answer_l10n_rows, "row")
                ET.SubElement(l10n_row, "id").text = str(aid)
                ET.SubElement(l10n_row, "aid").text = str(aid)
                ET.SubElement(l10n_row, "qid").text = str(q["qid"])
                ET.SubElement(l10n_row, "answer").text = text
                ET.SubElement(l10n_row, "language").text = "en"

                aid += 1

        # Multiple short text → subquestions
        if q["type"] == "Q":
            sq_order = 1
            for sq in q["subquestions"]:
                sqrow = ET.SubElement(subq_rows, "row")
                ET.SubElement(sqrow, "qid").text = str(subq_id)
                ET.SubElement(sqrow, "parent_qid").text = str(q["qid"])
                ET.SubElement(sqrow, "sid").text = str(sid)
                ET.SubElement(sqrow, "gid").text = str(gid)
                ET.SubElement(sqrow, "type").text = "T"
                ET.SubElement(sqrow, "title").text = cdata(sq["code"])
                ET.SubElement(sqrow, "question_order").text = str(sq_order)
                ET.SubElement(sqrow, "scale_id").text = "0"

                l10n_row = ET.SubElement(subq_l10n_rows, "row")
                ET.SubElement(l10n_row, "id").text = str(subq_id)
                ET.SubElement(l10n_row, "qid").text = str(subq_id)
                ET.SubElement(l10n_row, "question").text = cdata(sq["text"])
                ET.SubElement(l10n_row, "language").text = "en"

                subq_id += 1
                sq_order += 1

        # Validation for open questions
        if q["type"] == "S" and q.get("answers"):
            valid_expr = " or ".join([f"regexMatch('/^{a}$/', this)" for a in q["answers"]])
            vrow = ET.SubElement(q_attr_rows, "row")
            ET.SubElement(vrow, "qid").text = str(q["qid"])
            ET.SubElement(vrow, "attribute").text = "em_validation_q"
            ET.SubElement(vrow, "value").text = valid_expr
            ET.SubElement(vrow, "language")

        # Feedback if available
        if q.get("feedback"):
            frow = ET.SubElement(q_attr_rows, "row")
            ET.SubElement(frow, "qid").text = str(q["qid"])
            ET.SubElement(frow, "attribute").text = "em_validation_q_tip"
            ET.SubElement(frow, "value").text = cdata(q["feedback"])
            ET.SubElement(frow, "language").text = "en"

        q_order += 1

    return prettify(doc)

if __name__ == "__main__":
    lesson_path = "questions/English/1/"
    lesson_data = load_lesson_data(lesson_path, "Lesson 1", 1)
    xml_str = build_lsg_xml(lesson_data)
    with open("lesson1_fixed.lsg", "w", encoding="utf-8") as f:
        f.write(xml_str)
    print("lesson1_fixed.lsg generated with answers, subquestions, and feedback.")
