atoms(p;q;r).

head(1, 2).

choice(2, p).
choice_left(2, 0).
choice_right(2, 1).

head(3, q).
body(3, naf(q)).
body(3, p).
body(3, neg(r)).

head(4, 5).

choice(5, r).
choice_left(5, 0).
choice_right(5, 1).

undefined(q).
