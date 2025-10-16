def prompt_finance(question, top_matches, intro, instructions):

    context = "Voici les éléments Power BI disponibles : \n"
    for match in top_matches:
        workspace = match.get("workspace", "inconnu")
        report = match.get("report", "inconnu")
        page = match.get("page", None)
        if page:
            context += f" - Rapport : {report}, Page : {page} (workspace : {workspace})\n"
        else:
            context += f" - Rapport : {report} (workspace : {workspace})\n"
    
    question_utilisateur = f"\nQuestion utilisateur : {question}\n\n"

    return f"{intro}\n\n{context}\n{question_utilisateur}\n{instructions}"
