def generate_prompt_free(question, intro, instructions):
    question_utilisateur = f"\nQuestion utilisateur : {question}\n\n"

    return f"{intro}\n\n{question_utilisateur}\n{instructions}"
