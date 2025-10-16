def generate_prompt(top_matches, intro, instructions):
    
    context = "Here are the 30 most relevant Power BI elements: \n"
    for match in top_matches:
        workspace = match.get("workspace", "unknown")
        report = match.get("report", "unknown")
        page = match.get("page", None)
        if page:
            context += f" ** Workspace : {workspace}**  \n"
            context += f"      Report: *{report}*  \n"
            context += f"           Page: *{page}* \n"
        else:
            context += f" - Report: {report} (workspace: {workspace})\n"

    return f"{intro}\n\n{instructions}\n\n{context}"


def generate_prompt_rag(top_matches, intro, instructions):
    
    context = "Here are the 30 most relevant Power BI elements: \n"
    for match in top_matches:
        workspace = match.get("workspace", "unknown")
        report = match.get("report", "unknown")
        page = match.get("page", None)
        if page:
            context += f" ** Workspace : {workspace}**  \n"
            context += f"      Report: *{report}*  \n"
            context += f"           Page: *{page}* \n"
        else:
            context += f" - Report: {report} (workspace: {workspace})\n"

    return f"{intro}\n\n{instructions}\n\n{context}"
