atom(a;b;c;d;e).

% (i)
head(1, a).
body(1, naf(b)).

% (ii)
head(2, neg(a)).
body(2, naf(c)).

% (iii)
head(3, d).
body(3, naf(a)).

% (iv)
head(4, e).
body(4, naf(neg(a))).
