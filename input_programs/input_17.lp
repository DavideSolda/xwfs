atoms(p;q).

% 0{p}1.
head(1, 2).
choice(2, p).
choice_left(2, 0).
choice_right(2, 1).

% q :- not p.
head(3, q).
body(3, naf(p)).

% p :- not q.
head(4, p).
body(4, naf(q)).

% q must be undefined
not_undefined(q).
