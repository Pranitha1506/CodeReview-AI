
import ast
import difflib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY", "")

DEFAULT_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
]

MODEL_LIST = os.getenv("GEMINI_MODELS", "").strip()

GEMINI_MODELS = (
    [model.strip() for model in MODEL_LIST.split(",") if model.strip()]
    if MODEL_LIST
    else DEFAULT_MODELS
)

client = (
    genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(timeout=15000)
    )
    if API_KEY
    else None
)


def extract_json(response_text: str) -> Dict[str, Any]:
    """Extract JSON safely from a Gemini response."""

    if not response_text:
        raise ValueError("Gemini returned an empty response.")

    text = response_text.strip()

    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Gemini did not return valid JSON.")

    return json.loads(text[start:end + 1])


def generate_json(prompt: str) -> tuple[Dict[str, Any], str]:
    """
    Try every configured Gemini model in order.

    A failed model does not stop the next model from being tried.
    Returns the JSON response and the model that succeeded.
    """

    if client is None:
        raise RuntimeError(
            "Gemini API key is missing. Configure GEMINI_API_KEY in .env."
        )

    errors = []

    for model_name in GEMINI_MODELS:
        try:
            logger.info("Trying Gemini model: %s", model_name)

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=3072
                )
            )

            result = extract_json(response.text)

            logger.info("Gemini succeeded using model: %s", model_name)

            return result, model_name

        except Exception as error:
            message = str(error)

            logger.warning(
                "Gemini model %s failed: %s",
                model_name,
                message
            )

            errors.append(f"{model_name}: {message}")

            continue

    raise RuntimeError(
        "All configured Gemini models failed.\n"
        + "\n".join(errors)
    )


def offline_review_code(code: str, language: str) -> Dict[str, Any]:
    if language.lower() not in ("python", "py"):
        return {
            "overall_score": None,
            "summary": (
                "Gemini is unavailable. The offline review supports Python "
                f"only; {language} was not analyzed."
            ),
            "bugs": [],
            "security_issues": [],
            "optimizations": [],
            "code_quality": "Not assessed by the offline analyzer.",
            "improved_code": code,
            "source": "Offline Static Analyzer"
        }

    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        line = error.lineno or 1
        message = f"Python syntax error on line {line}: {error.msg}."
        return {
            "overall_score": None,
            "summary": (
                "Gemini is unavailable. Offline syntax validation found an issue; "
                "a full code review was not performed."
            ),
            "bugs": [{
                "title": "Python syntax error",
                "description": message,
                "severity": "High"
            }],
            "security_issues": [],
            "optimizations": [],
            "code_quality": "Not assessed because the code did not parse.",
            "improved_code": code,
            "source": "Offline Static Analyzer"
        }

    bugs = []
    seen_findings = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue

        denominator = node.right
        description = None
        severity = "Medium"

        try:
            value = ast.literal_eval(denominator)
        except (ValueError, TypeError, SyntaxError):
            value = None
        else:
            if (
                isinstance(value, (int, float, complex))
                and not isinstance(value, bool)
                and value == 0
            ):
                description = "Division by a literal zero will raise ZeroDivisionError."
                severity = "High"

        if description is None and isinstance(denominator, ast.Name):
            description = (
                f"The denominator '{denominator.id}' may be zero; "
                "validate it before division."
            )
        elif (
            description is None
            and isinstance(denominator, ast.Call)
            and isinstance(denominator.func, ast.Name)
            and denominator.func.id == "len"
            and len(denominator.args) == 1
            and isinstance(denominator.args[0], ast.Name)
        ):
            description = (
                f"The collection '{denominator.args[0].id}' may be empty, "
                "making its length zero."
            )

        if description is None:
            continue

        line = node.lineno
        key = (line, description)
        if key in seen_findings:
            continue

        seen_findings.add(key)
        bugs.append({
            "title": "Potential division by zero",
            "description": f"Line {line}: {description}",
            "severity": severity
        })

    if bugs:
        summary = (
            "Gemini is unavailable. Limited offline Python checks found "
            f"{len(bugs)} potential division issue(s); a full review was not performed."
        )
    else:
        summary = (
            "Gemini is unavailable. Limited offline Python checks found no "
            "supported issues; this is not a full code review."
        )

    return {
        "overall_score": None,
        "summary": summary,
        "bugs": bugs,
        "security_issues": [],
        "optimizations": [],
        "code_quality": (
            "Python syntax parsed. The offline analyzer checks only syntax and "
            "simple division-by-zero risks; security, performance, and overall "
            "code quality were not assessed."
        ),
        "improved_code": code,
        "source": "Offline Static Analyzer"
    }


def review_code(code: str, language: str) -> Dict[str, Any]:
    """Perform an AI-powered code review."""

    if not code or not code.strip():
        raise ValueError("Please provide code for review.")

    prompt = f"""
You are an experienced software code reviewer.

Review the following {language} code carefully.

CODE:
{code}

Return ONLY valid JSON using exactly these keys:

{{
    "overall_score": 85,
    "summary": "Short overall review",
    "bugs": [
        {{
            "title": "Bug title",
            "description": "Explain the bug",
            "severity": "High"
        }}
    ],
    "security_issues": [
        {{
            "title": "Security issue",
            "description": "Explain the issue",
            "severity": "Medium"
        }}
    ],
    "optimizations": [
        {{
            "title": "Optimization",
            "description": "Explain the improvement"
        }}
    ],
    "code_quality": "Explain readability, structure and maintainability",
    "improved_code": "Provide improved code"
}}

Rules:
- overall_score must be an integer from 0 to 100.
- severity must be High, Medium, or Low.
- Do not invent bugs.
- If a category has no findings, return an empty array.
- Preserve the original programming language.
- Return valid JSON only.
"""

    try:
        result, model_used = generate_json(prompt)

        required_keys = [
            "overall_score",
            "summary",
            "bugs",
            "security_issues",
            "optimizations",
            "code_quality",
            "improved_code"
        ]

        for key in required_keys:
            if key not in result:
                raise ValueError(f"Gemini response is missing: {key}")

        result["overall_score"] = max(
            0,
            min(100, int(result["overall_score"]))
        )
        result["source"] = "Gemini AI"

        logger.info("Code review completed using %s", model_used)

        return result

    except Exception as error:
        logger.warning(
            "Gemini review process failed. Activating offline analyzer: %s",
            error
        )
        return offline_review_code(code, language)


def generate_diff(
    original_code: str,
    fixed_code: str
) -> List[Dict[str, Any]]:
    """Generate line-by-line differences."""

    original_lines = original_code.splitlines()
    fixed_lines = fixed_code.splitlines()

    matcher = difflib.SequenceMatcher(
        None,
        original_lines,
        fixed_lines
    )

    diff = []
    line_number = 1

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":
            for line in fixed_lines[j1:j2]:
                diff.append({
                    "type": "unchanged",
                    "line_number": line_number,
                    "content": line
                })
                line_number += 1

        elif tag == "delete":
            for line in original_lines[i1:i2]:
                diff.append({
                    "type": "removed",
                    "line_number": line_number,
                    "content": line
                })

        elif tag == "insert":
            for line in fixed_lines[j1:j2]:
                diff.append({
                    "type": "added",
                    "line_number": line_number,
                    "content": line
                })
                line_number += 1

        elif tag == "replace":
            for line in original_lines[i1:i2]:
                diff.append({
                    "type": "removed",
                    "line_number": line_number,
                    "content": line
                })

            for line in fixed_lines[j1:j2]:
                diff.append({
                    "type": "added",
                    "line_number": line_number,
                    "content": line
                })
                line_number += 1

    return diff


def validate_python(code: str):
    """Validate Python syntax without executing the code."""

    try:
        ast.parse(code)
        return True, "Python syntax is valid."

    except SyntaxError as error:
        return (
            False,
            f"Syntax error at line {error.lineno}: {error.msg}"
        )


def offline_fix_code(
    code: str,
    language: str
) -> Dict[str, Any]:
    """
    Limited offline analyzer.

    It does not execute user code.
    It only applies narrowly supported Python fixes.
    """

    original_code = code
    fixed_code = code

    changes = []
    remaining_issues = []
    testing_notes = []

    syntax_valid = None
    syntax_message = "Offline syntax validation is not available for this language."

    if language.lower() not in ("python", "py"):
        remaining_issues.append(
            "Offline automatic fixes currently support Python only."
        )

        testing_notes.append(
            "Retry when a Gemini model is available for AI-based fixes."
        )

        return {
            "language": language,
            "original_code": original_code,
            "fixed_code": fixed_code,
            "decision": "NO_FIX_NEEDED",
            "decision_reason": (
                "Gemini models were unavailable. "
                "The offline analyzer does not support automatic fixes "
                "for this programming language."
            ),
            "syntax_valid": None,
            "syntax_message": syntax_message,
            "summary": "Offline analysis completed with limited language support.",
            "changes": [],
            "remaining_issues": remaining_issues,
            "testing_notes": testing_notes,
            "diff": generate_diff(original_code, fixed_code),
            "source": "Offline Static Analyzer",
            "model_used": None
        }

    syntax_valid, syntax_message = validate_python(code)

    if not syntax_valid:
        remaining_issues.append(
            "Python syntax must be corrected before automatic analysis "
            "can safely continue."
        )

        testing_notes.append(
            "Correct the reported syntax error and submit the code again."
        )

        return {
            "language": language,
            "original_code": original_code,
            "fixed_code": original_code,
            "decision": "BUG_FIX_REQUIRED",
            "decision_reason": "The submitted Python code contains a syntax error.",
            "syntax_valid": False,
            "syntax_message": syntax_message,
            "summary": "Offline analysis detected a Python syntax error.",
            "changes": [],
            "remaining_issues": remaining_issues,
            "testing_notes": testing_notes,
            "diff": generate_diff(original_code, original_code),
            "source": "Offline Static Analyzer",
            "model_used": None
        }

    tree = ast.parse(code)
    lines = code.splitlines()

    insertions = []

    class DivisionChecker(ast.NodeVisitor):

        def visit_FunctionDef(self, node):
            self.check_function(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self.check_function(node)
            self.generic_visit(node)

        def check_function(self, node):

            for child in ast.walk(node):

                if not isinstance(child, ast.Return):
                    continue

                expression = child.value

                if not isinstance(expression, ast.BinOp):
                    continue

                if not isinstance(expression.op, ast.Div):
                    continue

                denominator = expression.right

                if isinstance(denominator, ast.Name):

                    variable = denominator.id

                    already_guarded = False

                    for statement in node.body:
                        if not isinstance(statement, ast.If):
                            continue

                        test = statement.test

                        if isinstance(test, ast.Compare):
                            names = [
                                item.id
                                for item in ast.walk(test)
                                if isinstance(item, ast.Name)
                            ]

                            if variable in names:
                                already_guarded = True
                                break

                    if not already_guarded:
                        indentation = (
                            len(lines[child.lineno - 1])
                            - len(lines[child.lineno - 1].lstrip())
                        )

                        indent = " " * indentation
                        insertions.append((
                            child.lineno - 1,
                            [
                                f"{indent}if {variable} == 0:",
                                f'{indent}    raise ValueError("{variable} cannot be zero")'
                            ],
                            f"Added a zero-division guard for {variable}."
                        ))

                elif (
                    isinstance(denominator, ast.Call)
                    and isinstance(denominator.func, ast.Name)
                    and denominator.func.id == "len"
                    and len(denominator.args) == 1
                    and isinstance(denominator.args[0], ast.Name)
                ):

                    variable = denominator.args[0].id

                    indentation = (
                        len(lines[child.lineno - 1])
                        - len(lines[child.lineno - 1].lstrip())
                    )

                    indent = " " * indentation

                    insertions.append((
                        child.lineno - 1,
                        [
                            f"if not {variable}:",
                            f'    raise ValueError("{variable} cannot be empty")'
                        ],
                        f"Added an empty-input guard for {variable}."
                    ))

    DivisionChecker().visit(tree)

    for position, new_lines, explanation in sorted(
        insertions,
        key=lambda item: item[0],
        reverse=True
    ):
        lines[position:position] = new_lines

        changes.append({
            "title": "Added input validation",
            "explanation": explanation,
            "change_type": "Bug Fix"
        })

    if insertions:
        fixed_code = "\n".join(lines)

        if original_code.endswith("\n"):
            fixed_code += "\n"

    syntax_valid, syntax_message = validate_python(fixed_code)

    if not syntax_valid:
        fixed_code = original_code
        changes = []

        syntax_valid, syntax_message = validate_python(original_code)

        remaining_issues.append(
            "The offline analyzer could not safely validate its proposed changes."
        )

    if changes:
        decision = "BUG_FIX_REQUIRED"
        decision_reason = (
            "The offline analyzer found supported input-validation "
            "cases and added defensive checks."
        )
        summary = "Offline analyzer applied supported Python input-validation fixes."

    else:
        decision = "NO_FIX_NEEDED"
        decision_reason = (
            "No automatically supported issue was found by the offline rules. "
            "This does not guarantee that the code is bug-free."
        )
        summary = (
            "Offline analysis completed. No supported automatic fix was applied."
        )

        remaining_issues.append(
            "This offline analyzer checks only a limited set of Python patterns. "
            "It cannot replace a full AI code review."
        )

    testing_notes.append(
        "Run the code with normal inputs and edge cases after applying the result."
    )

    testing_notes.append(
        "Check zero values and empty collections where applicable."
    )

    return {
        "language": language,
        "original_code": original_code,
        "fixed_code": fixed_code,
        "decision": decision,
        "decision_reason": decision_reason,
        "syntax_valid": syntax_valid,
        "syntax_message": syntax_message,
        "summary": summary,
        "changes": changes,
        "remaining_issues": remaining_issues,
        "testing_notes": testing_notes,
        "diff": generate_diff(original_code, fixed_code),
        "source": "Offline Static Analyzer",
        "model_used": None
    }


def fix_code(
    code: str,
    language: str
) -> Dict[str, Any]:
    """Try Gemini models first, then use offline analysis."""

    if not code or not code.strip():
        raise ValueError("Please provide code to fix.")

    prompt = f"""
You are an expert software debugging and code improvement assistant.

Analyze and fix the submitted {language} code.

ORIGINAL CODE:
{code}

First decide whether the code needs:
1. NO_FIX_NEEDED
2. IMPROVEMENT
3. BUG_FIX_REQUIRED

Return ONLY valid JSON with these exact keys:

{{
    "decision": "BUG_FIX_REQUIRED",
    "decision_reason": "Explain why this decision was made.",
    "summary": "Summarize the result.",
    "fixed_code": "Complete corrected source code.",
    "changes": [
        {{
            "title": "Change title",
            "explanation": "Explain the change.",
            "change_type": "Bug Fix"
        }}
    ],
    "remaining_issues": [],
    "testing_notes": []
}}

Rules:
- decision must be NO_FIX_NEEDED, IMPROVEMENT, or BUG_FIX_REQUIRED.
- change_type must be Bug Fix, Security, Performance, Readability, or Other.
- Always return the complete source code in fixed_code.
- Preserve the original programming language.
- Do not remove working functionality.
- Do not invent bugs.
- If no changes are required, return the original code unchanged.
- Explain any issues that cannot be safely fixed.
- Return valid JSON only.
"""

    try:
        result, model_used = generate_json(prompt)

        required_keys = [
            "decision",
            "decision_reason",
            "summary",
            "fixed_code",
            "changes",
            "remaining_issues",
            "testing_notes"
        ]

        for key in required_keys:
            if key not in result:
                raise ValueError(
                    f"Gemini fix response is missing: {key}"
                )

        fixed_code = result["fixed_code"]

        if not isinstance(fixed_code, str):
            raise ValueError("Gemini returned an invalid fixed_code value.")

        if language.lower() in ("python", "py"):
            syntax_valid, syntax_message = validate_python(fixed_code)
        else:
            syntax_valid = None
            syntax_message = (
                "Automatic syntax validation is currently supported only for Python."
            )

        if syntax_valid is False:
            raise ValueError(
                "Gemini returned Python code with invalid syntax. "
                "Trying the next available model."
            )

        return {
            "language": language,
            "original_code": code,
            "fixed_code": fixed_code,
            "decision": result["decision"],
            "decision_reason": result["decision_reason"],
            "syntax_valid": syntax_valid,
            "syntax_message": syntax_message,
            "summary": result["summary"],
            "changes": result["changes"],
            "remaining_issues": result["remaining_issues"],
            "testing_notes": result["testing_notes"],
            "diff": generate_diff(code, fixed_code),
            "source": "Gemini AI",
            "model_used": model_used
        }

    except Exception as error:
        logger.warning(
            "Gemini fix process failed. Activating offline analyzer: %s",
            error
        )

        return offline_fix_code(code, language)
