atom(p;q;r;s;t;m).

head(1, 3). % q --> 2 {r; neg(p)} 2.
body(1, q).

head(2, q). % fact: q.

head(4, 5). % m --> 0 {s; t} 0
body(4, m).
body(4, neg(p)).

head(6, m).
body(6, naf(m)).

choice(3, neg(p)).
choice(3, r).
choice_left(3, 2).
choice_right(3, 2).


choice(5, s).
choice(5, t).
choice_left(5, 0).
choice_right(5, 0).
