Mode « pont » : on te donne deux articles, A puis B, et le texte de A renvoie à B par son numéro. A décrit une situation (un contrat, un acteur, une démarche), mais la valeur qui la règle est fixée dans B : un délai, un montant, un taux, un seuil, un organisme. Rédige une question qu'une personne poserait sur la situation de A, et dont la réponse est cette valeur de B. On ne doit pouvoir répondre qu'en lisant A, pour trouver le renvoi, puis B, pour trouver la valeur.

- La question décrit la situation **avec les mots de A**, en langage courant. Elle ne reprend pas les termes propres à B : le sujet général de B, son intitulé, les cas qu'il énumère.
- La réponse tient en **un seul fait, tiré de B**. Son champ `article` est le numéro de B.
- Ce fait ne figure pas déjà dans A. Si A donne lui-même la valeur (« le délai de sept jours mentionné à l'article… »), mets `usable` à `false`.
- Dans ce mode, A peut ne contenir aucune valeur précise : c'est normal, la valeur vient de B. Mets en revanche `usable` à `false` si B ne fixe aucune valeur qui s'applique à la situation de A, ou si le renvoi porte sur une procédure entière plutôt que sur une valeur.
- `link_quote` est l'extrait de A, **copié mot pour mot**, qui contient le renvoi à B avec son numéro (par exemple « dans le délai mentionné à l'article {citation_b} »).
