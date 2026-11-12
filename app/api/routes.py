
import json

from fastapi import APIRouter, HTTPException, Query

from app.schemas.review import (
    CodeSubmission,
    CodeReviewResponse,
    CodeFixRequest,
    CodeFixResponse
)

from app.services.gemini_service import (
    review_code,
    fix_code
)

from app.database.connection import (
    get_db_connection,
    create_all_tables
)


router = APIRouter()


create_all_tables()


def parse_json(value):
    """Safely convert a database JSON value into Python data."""

    if isinstance(value, str):
        return json.loads(value)

    return value if value is not None else {}


def close_database(cursor, connection):
    """Safely close database resources."""

    if cursor:
        cursor.close()

    if connection and connection.is_connected():
        connection.close()


def get_sort_order(sort, history_type="reviews"):
    """Return a safe SQL sorting expression."""

    if history_type == "reviews":
        allowed = {
            "newest": "created_at DESC",
            "oldest": "created_at ASC",
            "score-high": "overall_score DESC",
            "score-low": "overall_score ASC"
        }
    else:
        allowed = {
            "newest": "created_at DESC",
            "oldest": "created_at ASC"
        }

    return allowed.get(sort, "created_at DESC")


def count_review_bugs(review_result):
    """Count bug findings stored in a review result."""

    try:
        result = parse_json(review_result)

        bugs = result.get("bugs", [])

        return len(bugs) if isinstance(bugs, list) else 0

    except (ValueError, TypeError, AttributeError):
        return 0


@router.post(
    "/review",
    response_model=CodeReviewResponse
)
async def analyze_code(submission: CodeSubmission):

    connection = None
    cursor = None

    try:
        result = review_code(
            code=submission.code,
            language=submission.language
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO code_reviews
            (
                language,
                source_code,
                overall_score,
                review_result
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                submission.language,
                submission.code,
                result["overall_score"],
                json.dumps(result)
            )
        )

        connection.commit()

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.get("/reviews")
async def get_review_history(
    search: str = Query(default=""),
    language: str = Query(default="all"),
    sort: str = Query(default="newest")
):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                id,
                language,
                overall_score,
                created_at
            FROM code_reviews
            WHERE 1 = 1
        """

        params = []

        if language.lower() != "all":
            sql += " AND language = %s"
            params.append(language)

        if search.strip():
            search_value = search.strip()

            if search_value.isdigit():
                sql += """
                    AND (
                        id = %s
                        OR language LIKE %s
                    )
                """

                params.extend([
                    int(search_value),
                    f"%{search_value}%"
                ])

            else:
                sql += " AND language LIKE %s"
                params.append(f"%{search_value}%")

        sql += " ORDER BY " + get_sort_order(
            sort,
            "reviews"
        )

        cursor.execute(sql, tuple(params))

        return cursor.fetchall()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.get("/reviews/{review_id}")
async def get_review_details(review_id: int):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM code_reviews
            WHERE id = %s
            """,
            (review_id,)
        )

        review = cursor.fetchone()

        if not review:
            raise HTTPException(
                status_code=404,
                detail="Review not found"
            )

        review["review_result"] = parse_json(
            review["review_result"]
        )

        return review

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: int):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM code_reviews
            WHERE id = %s
            """,
            (review_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Review not found"
            )

        connection.commit()

        return {
            "message": "Review deleted successfully",
            "review_id": review_id
        }

    except HTTPException:
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.post(
    "/fix",
    response_model=CodeFixResponse
)
async def fix_submitted_code(request: CodeFixRequest):

    connection = None
    cursor = None

    try:
        result = fix_code(
            code=request.code,
            language=request.language
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO code_fix_history
            (
                language,
                original_code,
                fixed_code,
                decision,
                source,
                model_used,
                fix_result
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                request.language,
                result["original_code"],
                result["fixed_code"],
                result["decision"],
                result.get("source", "Gemini AI"),
                result.get("model_used"),
                json.dumps(result)
            )
        )

        connection.commit()

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.get("/fixes")
async def get_fix_history(
    search: str = Query(default=""),
    language: str = Query(default="all"),
    sort: str = Query(default="newest")
):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                id,
                language,
                decision,
                source,
                model_used,
                created_at
            FROM code_fix_history
            WHERE 1 = 1
        """

        params = []

        if language.lower() != "all":
            sql += " AND language = %s"
            params.append(language)

        if search.strip():
            search_value = search.strip()

            if search_value.isdigit():
                sql += """
                    AND (
                        id = %s
                        OR language LIKE %s
                    )
                """

                params.extend([
                    int(search_value),
                    f"%{search_value}%"
                ])

            else:
                sql += " AND language LIKE %s"
                params.append(f"%{search_value}%")

        sql += " ORDER BY " + get_sort_order(
            sort,
            "fixes"
        )

        cursor.execute(sql, tuple(params))

        return cursor.fetchall()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.get("/fixes/{fix_id}")
async def get_fix_details(fix_id: int):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM code_fix_history
            WHERE id = %s
            """,
            (fix_id,)
        )

        fix = cursor.fetchone()

        if not fix:
            raise HTTPException(
                status_code=404,
                detail="Fix history record not found"
            )

        fix["fix_result"] = parse_json(
            fix["fix_result"]
        )

        return fix

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.delete("/fixes/{fix_id}")
async def delete_fix_history(fix_id: int):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM code_fix_history
            WHERE id = %s
            """,
            (fix_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Fix history record not found"
            )

        connection.commit()

        return {
            "message": "Fix history deleted successfully",
            "fix_id": fix_id
        }

    except HTTPException:
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)


@router.get("/dashboard")
async def get_dashboard_statistics():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_reviews,
                COALESCE(AVG(overall_score), 0) AS average_score
            FROM code_reviews
            """
        )

        review_stats = cursor.fetchone()

        cursor.execute(
            """
            SELECT review_result
            FROM code_reviews
            """
        )

        review_records = cursor.fetchall()

        total_bugs = sum(
            count_review_bugs(record["review_result"])
            for record in review_records
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total_fixes
            FROM code_fix_history
            """
        )

        fix_stats = cursor.fetchone()

        return {
            "total_reviews": int(
                review_stats["total_reviews"]
            ),

            "total_fixes": int(
                fix_stats["total_fixes"]
            ),

            "average_score": round(
                float(review_stats["average_score"] or 0),
                2
            ),

            "total_bugs": int(total_bugs)
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        close_database(cursor, connection)
