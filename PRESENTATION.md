# Power BI Navigation Assistant
## Présentation orale

---

## Le problème

Aujourd'hui, les équipes ont accès à des dizaines de workspaces Power BI, avec des centaines de rapports et des milliers de pages. Quand on cherche une information précise, on perd du temps à naviguer dans les menus, à ouvrir plusieurs rapports, ou à demander aux collègues "c'est où déjà le rapport sur les encours ?".

---

## Notre solution

On a créé un assistant intelligent où l'utilisateur pose sa question en langage naturel, comme à un collègue, et l'assistant lui répond directement avec les bons rapports.

Par exemple : "Je cherche les infos sur la trésorerie" → l'assistant sort les rapports pertinents avec les liens cliquables.

---

## Comment ça marche ? (en 3 étapes)

### Étape 1 : On prépare le terrain (une seule fois)

On récupère toutes les métadonnées Power BI : les noms des workspaces, des rapports, des pages. Ensuite, on transforme chaque élément en une sorte d'empreinte numérique qu'on appelle "embedding".

C'est comme donner des coordonnées GPS à chaque rapport. Deux rapports qui parlent du même sujet auront des coordonnées proches, même s'ils n'utilisent pas exactement les mêmes mots.

Ces empreintes sont stockées une seule fois dans des fichiers locaux. On ne refait ce travail que si les rapports Power BI changent.

---

### Étape 2 : La recherche intelligente (à chaque question)

Quand un utilisateur pose une question, on transforme sa question en empreinte numérique avec la même méthode.

Ensuite, on compare cette empreinte avec toutes celles qu'on a stockées. C'est un calcul mathématique simple (similarité cosinus) qui mesure la proximité entre deux empreintes. On récupère les 50 rapports les plus proches de la question.

L'avantage par rapport à une recherche classique par mots-clés : le système comprend le sens. Si tu cherches "encours", il trouvera aussi les rapports qui parlent d'"outstanding" même si le mot "encours" n'apparaît pas.

---

### Étape 3 : La réponse en langage naturel (IA générative)

On envoie les 50 résultats pertinents à un modèle de langage (GPT-4o, GPT-4.1, etc.), avec la question de l'utilisateur.

Le modèle formule une réponse claire et naturelle, en recommandant les rapports les plus adaptés avec une explication.

---

## Le glossaire : un plus pour chaque équipe

Chaque équipe peut maintenir un fichier Excel avec ses définitions métier. Par exemple, ce que signifie "LCR", "NSFR" ou "Gap" dans son contexte.

Ces définitions sont automatiquement ajoutées au contexte envoyé à l'IA, ce qui améliore la pertinence des réponses pour le vocabulaire spécifique de chaque équipe.

Les glossaires peuvent être stockés en local (par défaut) ou sur SharePoint pour un déploiement entreprise.

---

## Isolation par équipe

Quand l'utilisateur se connecte, il choisit son équipe. L'assistant ne lui montre que les workspaces auxquels son équipe a accès. Finance voit ses rapports, Data Management voit les siens, etc.

Le mapping équipe → workspaces est défini dans `data/team_workspace_mapping.json`.

---

## Pourquoi pas une vraie base de données vectorielle ?

On utilise des fichiers locaux (numpy + pickle) plutôt qu'une base vectorielle dédiée comme Pinecone ou ChromaDB. C'est un choix de simplicité : pas d'infrastructure supplémentaire à maintenir, et c'est largement suffisant pour le volume actuel (quelques milliers d'entrées).

Si le volume explose un jour, on pourra migrer vers une solution plus robuste sans changer la logique applicative — il suffirait de remplacer les deux fonctions de chargement.

---

## Coûts maîtrisés

Point important : on n'appelle l'API d'embeddings qu'une seule fois par rapport, lors de l'indexation initiale. À chaque question utilisateur, on fait un seul appel pour transformer la question en vecteur, puis la recherche se fait en local.

Les coûts API sont donc prévisibles et maîtrisés.

---

## Stack technique en résumé

- **Interface** : Streamlit
- **Embeddings et LLM** : API OpenAI (compatible Azure OpenAI via `OPENAI_BASE_URL`)
- **Stockage des vecteurs** : fichiers NumPy et Pickle en local
- **Glossaires** : Excel local par défaut, SharePoint en option
- **Métadonnées Power BI** : API REST Power BI

---

## En une phrase

C'est un système RAG (Retrieval-Augmented Generation) qui combine recherche sémantique et IA générative pour aider les utilisateurs à trouver leurs rapports Power BI en langage naturel.
