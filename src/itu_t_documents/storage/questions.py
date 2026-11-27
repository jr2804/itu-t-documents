"""Write a question under study and its people into the metadata store."""

from __future__ import annotations

from sqlmodel import Session, select

from itu_t_documents.models.questions import Question
from itu_t_documents.storage.tables import PersonRow, QuestionRow, StudyGroupRow, row_id


def write_question(session: Session, question: Question, period_label: str) -> None:
    """Insert or update a question under study and its people.

    Args:
        session: The database session to write in; it is committed here.
        question: The question to store.
        period_label: The study period the question belongs to.
    """
    group = session.exec(
        select(StudyGroupRow).where(
            StudyGroupRow.period_label == period_label,
            StudyGroupRow.number == question.study_group,
        )
    ).first()
    if group is None:
        group = StudyGroupRow(period_label=period_label, number=question.study_group)
        session.add(group)
        session.flush()

    row = session.exec(
        select(QuestionRow).where(
            QuestionRow.study_group_id == group.id,
            QuestionRow.number == question.number,
        )
    ).first()
    if row is None:
        row = QuestionRow(study_group_id=row_id(group), number=question.number)
        session.add(row)
    row.title = question.title
    row.working_group = question.working_group.code
    session.flush()

    # The people of a question change with the published structure, so the
    # stored ones are replaced instead of appended to on every sync.
    question_id = row_id(row)
    for person_row in session.exec(select(PersonRow).where(PersonRow.question_id == question_id)).all():
        session.delete(person_row)
    session.flush()

    for person in question.people:
        session.add(
            PersonRow(
                question_id=question_id,
                name=person.name,
                role=person.role.value,
                organization=person.organization,
                country=person.country,
                email=person.email,
                phone=person.phone,
                fax=person.fax,
            )
        )
    session.commit()
