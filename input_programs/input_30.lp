

atoms(prec(a, b); prec(b, a); prec(a, c); dom(a); dom(b); dom(c); property(a, aa); property(b, bb); property(c, cc); holds(a, aa); holds(b, bb); holds(c, cc)).  

%facts: prec(a, b), prec(b, a), prec(a, c).

head(0, prec(a, b)).
head(1, prec(b, a)).
head(2, prec(a, c)).

%dominated(X) :- prec(X, Y).

head(3, overwritten(ob_a, permissive_a)).
body(3, prec(ob_a, ob_b)).

head(4, dom(b)).
body(4, po(b, a)).

head(5, dom(a)).
body(5, po(a, c)).


% facts: property

head(6, property(a, aa)).
head(7, property(b, bb)).
head(8, property(c, cc)).

%output(X, P) :- po(X, Y), property(X, P), not dominated(X).

head(9, output(a, aa)).
body(9, naf(dom(a))).
body(9, property(a, aa)).

head(10, output(b, bb)). 
body(10, naf(dom(b))).
body(10, property(b, bb)).

head(11, output(c, cc)).
body(11, naf(dom(c))).
body(11, property(c, cc)).

