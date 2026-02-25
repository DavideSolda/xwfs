atom(p;q;r;s;t;m).

head(1, 3). % q --> 2 {r; neg(p)} 2.
body(1, q).

head(2, q). % not q --> q.
body(2, naf(q)).

head(4, 5). % m --> 1 {s; t} 1
body(4, r).
body(4, neg(p)).

choice(3, neg(p)).
choice(3, r).
choice_left(3, 2).
choice_right(3, 2).


choice(5, s).
choice(5, t).
choice_left(5, 1).
choice_right(5, 1).
