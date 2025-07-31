# ExamPaperWebScraper

## High-Level Approach

- This tool focuses on extracting questions from a single, complex ACT International Subject Test Maths PDF rather than a generic or simplified file. https://www.act.org/content/dam/act/unsecured/documents/AIST-Math-Practice-Test.pdf    
- The pipeline:
    - Downloads the ACT sample PDF.
    - Extracts text and parses questions, options, and answers per page using pdfplumber and regular expressions.
    - Extracts answer key and matches each answer to its question.
    - Converts detected equations to Latex format for clarity.
    - Associates each question with its page number, referencing a single PNG image of the full page (not individual diagrams).

## Assumptions & Limitations

- Only public, freely accessible PDF used -> https://www.act.org/robots.txt
- Diagrams/images are not pinpointed for each question; instead, questions refer to their entire page image. 
    - This saves time and avoids complex image processing, keeping within a ~2 hour implementation window, only about half of the questions are successfully parsed; however, those parsed are processed to a good, readable structured format suitable for review or further processing.
- Some questions might be missed or incompletely parsed due to formatting irregularities within the PDF.

# Setup

## Create virtual environment
`python3 -m venv exam_extraction_env`

## Activate it
`source exam_extraction_env/bin/activate`

## To Deactive:

`deactivate`

## Install requirements in venv

`pip install -r ./requirements.txt`

## Run 

`python act_extractor.py`


# Output

- Each question record includes:
    - question text
    - options
    - correct answer
    - equations (LaTeX, if present)
    - source page number
- Each page associated with a question is saved as PNG.