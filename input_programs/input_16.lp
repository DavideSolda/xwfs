atoms(p;q).

head(1, 2).

choice(2, p).
choice_left(2, 0).
choice_right(2, 1).

head(3, q).
body(3, naf(q)).
body(3, p).

not_undefined(q).
