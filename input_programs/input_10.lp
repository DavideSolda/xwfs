atom(p;q;r;s;t;m).

dom(a).

head(1, three(X)) :- dom(X).    % q(X) --> 2 {r(X); neg(p(X))} 2.
body(1, q(X)) :- dom(X).

head(2, q(a)). % not q(a) --> q(a).
body(2, naf(q(a))).

head(4, 5).    % m --> 1 {s; t} 1
body(4, r_1).
body(4, neg(p_1)).

choice(three(X), neg(p(X))) :- dom(X).
choice(three(X), r(X)) :- dom(X).
choice_left(three(X), 2) :- dom(X).
choice_right(three(X), 2) :- dom(X).

choice(5, s).
choice(5, t).
choice_left(5, 1).
choice_right(5, 1).
