atom(p; s; r; t; q; c).

% 0{p}1
head(1, neg(p)).
%head(1, 2).
%choice(2, p).
%choice_left(2, 0).
%choice_right(2, 1).


% r <- not s.
head(3, r).
body(3, naf(s)).

% t <- q, not r.
head(4, t).
body(4, q).
body(4, naf(r)).

% q <- not p.
head(5, q).
body(5, naf(p)).

% s <- not t.
head(6, s).
body(6, naf(t)).

% c <- not s.
head(7, c).
body(7, naf(s)).

%not_undefined(c).
