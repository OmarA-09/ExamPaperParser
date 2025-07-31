
"""
ACT Maths Parser – designed for ACT International Subject Test format
Extracts most of Questions with page association rather than image association due to time constraints
Each answer to each question is extracted correctly
Some questions include equations list
"""

import requests
import json
import re
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging
import pdfplumber

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ACTQuestion:
    question_id: str
    question_type: str
    question_text: str
    options: List[Dict[str, str]] = None
    answer: str = None
    equations: List[str] = None
    page: int = None
    image: str = None

    def to_json_format(self) -> Dict:
        result = {
            "question_id": self.question_id,
            "question_type": self.question_type,
            "question_text": self.question_text,
            "page": self.page,
            "image": self.image
        }
        if self.options:
            result["options"] = self.options
        if self.answer:
            result["answer"] = self.answer
        if self.equations:
            result["equations"] = self.equations
        return result

class ACTParser:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.url = 'https://www.act.org/content/dam/act/unsecured/documents/AIST-Math-Practice-Test.pdf'
        self.answers = {}

    def clean_option_text(self, text: str) -> str:
        """Clean option text, handling ACT fraction notation."""
        
        text = re.sub(r'_(\d+)', r'-\1', text)  # _11 -> -11
        text = re.sub(r'_\s*(\d+)', r'-\1', text)  # _ 11 -> -11

        text = re.sub(r'©.*?All rights reserved\.', '', text)
        text = re.sub(r'No part of.*?transferred\.', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def is_actual_question(self, text: str) -> bool:
        """Check if this is a real maths question."""
        exclude_phrases = [
            "Illustrative figures", "Geometric figures lie",
            "The word line indicates", "Do not linger",
            "If I get a job"  
        ]
        include_phrases = [
            "What is", "Which", "Find", "Calculate", "Solve",
            "equation", "expression", "graph", "function"
        ]
        text_lower = text.lower()
        if any(phrase.lower() in text_lower for phrase in exclude_phrases):
            return False
        if any(phrase.lower() in text_lower for phrase in include_phrases):
            return True
        return '?' in text

    def download_pdf(self, filename: str = "act_math.pdf") -> bool:
        """Download ACT PDF."""
        try:
            print(f"Downloading ACT Maths PDF...")
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {filename}")
            return True
        except Exception as e:
            print(f" Download failed: {e}")
            return False

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from ACT PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n\n"
                print(f"Extracted {len(full_text)} characters from {len(pdf.pages)} pages")
                return full_text
        except Exception as e:
            print(f" PDF extraction failed: {e}")
            return ""

    def parse_answer_key(self, text: str):
        """Extract answer key from ACT PDF."""
        print("Parsing ACT answer key...")
        answer_key_start = text.find("Answer Key")
        if answer_key_start == -1:
            print(" Answer key section not found")
            return
        answer_section = text[answer_key_start:]
        pattern = r'(\d+)\s+([A-D])'
        matches = re.findall(pattern, answer_section)
        for question_num, answer_letter in matches:
            self.answers[question_num] = answer_letter
        print(f"Extracted {len(self.answers)} answers from answer key")

    def convert_to_latex(self, text: str) -> List[str]:
        """Convert mathematical expressions to LaTeX format."""
        equations = []
        latex_patterns = [
            (r'x\s*²', r'x^2'),
            (r'(\w+)\s*\^\s*(\d+)', r'\1^{\2}'),
            (r'√\s*(\w+)', r'\\sqrt{\1}'),
            (r'(\d+)/(\d+)', r'\\frac{\1}{\2}'),
            (r'∠(\w+)', r'\\angle \1'),
            (r'≤', r'\\leq'),
            (r'≥', r'\\geq'),
            (r'÷', r'\\div'),
            (r'×', r'\\times'),
        ]
        math_patterns = [
            r'[x-z]\s*[²³⁴]',
            r'[x-z]\s*\^\s*\d+',
            r'\d+\s*/\s*\d+',
            r'√\w+',
            r'∠\w+',
            r'[≤≥÷×]',
        ]
        for pattern in math_patterns:
            matches = re.findall(pattern, text)
            
            for match in matches:
                latex_expr = match
                
                for old_pattern, new_pattern in latex_patterns:
                    latex_expr = re.sub(old_pattern, new_pattern, latex_expr)
                
                if latex_expr not in equations:
                    equations.append(latex_expr)
        return equations

    def split_question_and_options(self, content: str) -> tuple:
        """Split question text from multiple choice options."""
        option_match = re.search(r'\n\s*([A-D])\.\s+', content)
        if option_match:
            split_pos = option_match.start()
            question_text = content[:split_pos].strip()
            options_text = content[split_pos:].strip()
            options = self.extract_options_precise(options_text)
            return question_text, options
        else:
            return content.strip(), []

    def extract_options_precise(self, options_text: str) -> List[Dict[str, str]]:
        """Extract options with precise boundary detection."""
        options = []
        option_pattern = r'([A-D])\.\s+(.*?)(?=\n\s*[A-D]\.\s+|\Z)'
        matches = re.findall(option_pattern, options_text, re.DOTALL)
        
        for key, text in matches:
            text = text.strip()
            text = self.clean_option_text(text)
            
            if len(text) > 0:
                options.append({
                    "key": key,
                    "text": text
                })
        return options

    def clean_question_text(self, text: str) -> str:
        """Clean question text."""
        text = re.sub(r'©.*?All rights reserved\.', '', text)
        text = re.sub(r'No part of.*?transferred\.', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def process_question_content(self, question_num: int, content: str, page_num: int, image_fname: str) -> Optional[ACTQuestion]:
        """Process one question content."""
        question_text, options = self.split_question_and_options(content)
        
        if not question_text or len(question_text) < 5:
            return None
        question_text = self.clean_question_text(question_text)
        
        if not self.is_actual_question(question_text):
            return None 
        equations = self.convert_to_latex(question_text)
        q_type = "single_choice" if options and len(options) >= 3 else (
            "application_questions" if any(
                k in question_text.lower() for k in ['calculate', 'solve', 'find', 'what is']
            ) else "fill_in_blank"
        )
        answer = self.answers.get(str(question_num))
        return ACTQuestion(
            question_id=f"act_math_{question_num}",
            question_type=q_type,
            question_text=question_text,
            options=options if options else None,
            answer=answer,
            equations=equations if equations else None,
            page=page_num,
            image=image_fname
        )

    def try_page_by_page_extraction(self, pdf_path: str) -> List[ACTQuestion]:
        """Extract questions page by page, saving only one image for each page with questions."""
        questions = []
        page_to_image = {}
        try:
            os.makedirs("output", exist_ok=True)
            with pdfplumber.open(pdf_path) as pdf:
                print(f"Attempting page-by-page extraction from {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    
                    if not page_text:
                        continue
                    markers = list(re.finditer(r'^\s*(\d+)\.\s+', page_text, re.MULTILINE))
                    
                    if not markers:
                        continue

                    if page_num not in page_to_image:
                        image_fname = f"output/page_{page_num}.png"
                        try:
                            page.to_image(resolution=200).save(image_fname, format="PNG")
                        except Exception as e:
                            image_fname = None
                        page_to_image[page_num] = image_fname
                    image_fname = page_to_image[page_num]

                    for i, match in enumerate(markers):
                        qnum = int(match.group(1))
                        start = match.end()
                        end = markers[i + 1].start() if i + 1 < len(markers) else len(page_text)
                        q_content = page_text[start:end].strip()
                        result = self.process_question_content(qnum, q_content, page_num, image_fname)
                        if result:
                            questions.append(result)
        except Exception as e:
            print(f"Page-by-page extraction failed: {e}")
        return questions

    def save_to_json(self, questions: List[ACTQuestion], filename: str = "act_math_questions.json"):
        """Save questions to JSON file (with page and image references) in output/ folder."""
        os.makedirs('output', exist_ok=True)
        filepath = os.path.join('output', filename)
        json_data = [q.to_json_format() for q in questions]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(questions)} ACT questions to {filepath}")

    def extract_all(self):
        """Complete extraction process."""
        print("ACT Maths Parser")
        print("=" * 40)
        
        if not self.download_pdf():
            return []
        text = self.extract_text_from_pdf("act_math.pdf")
        
        if not text:
            return []
        self.parse_answer_key(text)
        print("Using per-page visual extraction...")
        questions = self.try_page_by_page_extraction("act_math.pdf")
        
        if questions:
            self.save_to_json(questions)
            print(f"\n ACT Extraction Summary :")
            print(f"   Total questions: {len(questions)}")
            sample = questions[0]
            print(f"\n Sample question:")
            print(f"   {sample.question_text[:80]}...")
            if sample.options:
                for opt in sample.options[:2]:
                    print(f"   {opt['key']}) {opt['text'][:30]}...")
            if sample.answer:
                print(f"   Answer: {sample.answer}")
        try:
            os.remove("act_math.pdf")
        except Exception:
            pass
        return questions

if __name__ == "__main__":
    print("Starting ACT Maths extraction...")
    parser = ACTParser()
    questions = parser.extract_all()
    if questions:
        print(f"\n ACT extraction complete.")
        print(f" See: output/act_math_questions.json")
        print(f" Extracted {len(questions)}/50 questions")
    else:
        print(" No questions extracted")
