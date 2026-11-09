Mode « pont » : on te donne deux articles, A puis B, et l'un renvoie à l'autre par son numéro. La question part de la situation que décrit A, et sa réponse est une valeur fixée par B : un délai, un montant, un taux, un seuil. On ne doit pouvoir répondre qu'en reliant les deux articles. Deux cas se présentent :
- **A renvoie à B** (« dans le délai mentionné à l'article L. 312-25 ») : B fixe la valeur qui règle la situation de A ;
- **B renvoie à A** : B est souvent l'article qui sanctionne l'obligation décrite par A (« tout manquement à l'article L. 112-3 est passible d'une amende de 3 000 euros »). La question porte alors sur ce que risque le professionnel qui ne respecte pas cette obligation (« Un artisan ne m'a pas dit comment il calculait son devis : il risque quoi ? »).

- La question décrit la situation **avec les mots de A**, en langage courant. Elle ne reprend pas les termes propres à B (son sujet général, son intitulé, les cas qu'il énumère).
- La réponse tient en **un seul fait, tiré de B**. Son champ `article` est le numéro de B. Ce fait ne figure pas déjà dans A.
- Dans ce mode, A peut ne contenir aucune valeur précise : c'est normal, la valeur vient de B. Mets en revanche `usable` à `false` si B ne fixe aucune valeur qui s'applique à la situation de A, si A donne déjà la valeur, ou si le renvoi porte sur une procédure entière plutôt que sur une valeur.
- `link_quote` est l'extrait, **copié mot pour mot**, de l'article qui contient le renvoi (A ou B), avec le numéro de l'autre article.
