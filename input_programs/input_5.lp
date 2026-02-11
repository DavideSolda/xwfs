atom(p;q;r).

head(1, 3).
body(1, q).
head(2, q).

choice(3, neg(p)).
choice(3, r).
choice_left(3, 1).
choice_right(3, 1).
