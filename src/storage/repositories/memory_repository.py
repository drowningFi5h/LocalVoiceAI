from models.memory import Memory

from storage.database import Database


class MemoryRepository:

    def __init__(
        self,
        database: Database,
    ):

        self.db = database

    def add(
        self,
        memory: Memory,
    ) -> None:

        cursor = self.db.connection.cursor()

        cursor.execute(
            """
            INSERT INTO memories (

                memory_type,

                category,

                key,

                value,

                importance,

                confidence

            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                memory.memory_type,
                memory.category,
                memory.key,
                memory.value,
                memory.importance,
                memory.confidence,
            ),
        )

        self.db.connection.commit()

    def find_by_identity(
        self,
        memory_type: str,
        category: str,
        key: str,
    ) -> Memory | None:

        cursor = self.db.connection.cursor()

        cursor.execute(
            """
            SELECT *

            FROM memories

            WHERE

                memory_type=?

                AND category=?

                AND key=?
            """,
            (
                memory_type,
                category,
                key,
            ),
        )

        row = cursor.fetchone()

        if row is None:

            return None

        return Memory(

            id=row["id"],

            memory_type=row["memory_type"],

            category=row["category"],

            key=row["key"],

            value=row["value"],

            importance=row["importance"],

            confidence=row["confidence"],

            created_at=row["created_at"],

            updated_at=row["updated_at"],

            last_used=row["last_used"],

            use_count=row["use_count"],

        )

    def update(
        self,
        memory: Memory,
    ) -> None:

        cursor = self.db.connection.cursor()

        cursor.execute(
            """
            UPDATE memories

            SET

                value=?,

                importance=?,

                confidence=?,

                updated_at=CURRENT_TIMESTAMP,

                use_count=?

            WHERE id=?
            """,
            (
                memory.value,
                memory.importance,
                memory.confidence,
                memory.use_count,
                memory.id,
            ),
        )

        self.db.connection.commit()

    def get_all(
        self,
        memory_type: str,
    ) -> list[Memory]:

        cursor = self.db.connection.cursor()

        cursor.execute(
            """
            SELECT *

            FROM memories

            WHERE memory_type=?
            """,
            (memory_type,),
        )

        rows = cursor.fetchall()

        return [

            Memory(

                id=row["id"],

                memory_type=row["memory_type"],

                category=row["category"],

                key=row["key"],

                value=row["value"],

                importance=row["importance"],

                confidence=row["confidence"],

                created_at=row["created_at"],

                updated_at=row["updated_at"],

                last_used=row["last_used"],

                use_count=row["use_count"],

            )

            for row in rows

        ]