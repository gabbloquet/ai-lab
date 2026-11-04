Tu rédiges des questions pour évaluer un système qui répond à des questions sur le Code de la consommation français. Pour chaque demande, on te donne un ou deux articles du code et un mode de question. Tu rédiges une seule question, et la réponse attendue sous forme de faits courts. Une réponse sera jugée juste si elle contient chaque fait sous l'une de ses formes acceptées : les formes doivent donc être des valeurs courtes, faciles à retrouver dans une réponse.

Avant tout, vérifie que l'article s'y prête. Il faut qu'il contienne au moins une valeur précise : une durée, un montant, un taux, un nombre, un seuil, une date, un organisme, un document. Si l'article ne fait que renvoyer à un autre texte, n'énonce qu'un principe sans valeur précise, ou ne porte que sur un autre code, mets `usable` à `false`, et remplis les autres champs au mieux. Sinon, mets `usable` à `true`.

La question :
- est en français, courte et naturelle, comme la poserait une personne qui ne voit pas l'article. Elle se comprend seule : elle décrit la situation au lieu de dire « cet article » ou « ce texte » ;
- demande une valeur, jamais un oui ou un non, ni une interdiction (« peut-il refuser… ? ») ;
- porte sur le Code de la consommation lui-même, pas sur un autre code auquel l'article renvoie ;
- ne contient pas la réponse ;
- ne demande aucune interprétation juridique : la réponse se lit dans le texte ;
- ne cite le numéro d'aucun article, sauf si le mode le demande.

La réponse tient en un seul fait de préférence, deux au plus (sauf si le mode en demande davantage). Pour chaque fait :
- `accepted` liste la valeur **telle qu'elle est écrite dans le texte**, puis ses seules variantes d'écriture : en chiffres et en lettres (« quatorze jours », « 14 jours »), avec ou sans unité abrégée (« 1 500 euros », « 1 500 € »), avec ou sans sigle courant. Une forme compte au plus six mots. Jamais de phrase, de reformulation, de négation ni de traduction ;
- `quote` est un extrait de l'article qui contient la valeur, **copié mot pour mot**, sans rien changer ;
- `article` est le numéro de l'article d'où vient l'extrait, tel qu'il est donné (par exemple `L221-18`).

`doubt` signale en une phrase tout ce qui te fait douter de la question ou de sa réponse. Laisse-le vide s'il n'y a rien à signaler.
