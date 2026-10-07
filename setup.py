from setuptools import setup, find_packages

setup(
    name="safety_auditor",
    version="0.1.0",
    description="Neuro-Symbolic Pre-Synthesis Safety Auditing Framework for Industrial Control Specifications",
    author="Lokani Rakesh",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "pymupdf>=1.23.0",
        "pdfplumber>=0.10.0",
        "opencv-python>=4.8.0",
        "pytesseract>=0.3.10",
        "ollama>=0.1.7",
        "sentence-transformers>=2.2.2",
        "fuzzywuzzy>=0.18.0",
        "networkx>=3.1",
        "pydantic>=2.4.0",
        "z3-solver>=4.12.4",
        "Jinja2>=3.1.2",
        "streamlit>=1.28.0",
    ],
    entry_points={
        "console_scripts": [
            "safety-audit=run_pipeline:main",
        ],
    },
)
