literal(A)                :- atom(A).
literal(neg(A))           :- atom(A).
literal(naf(A))           :- atom(A).
literal(naf(neg(A)))      :- atom(A).
explicit_literal(A)       :- atom(A).
explicit_literal(neg(A))  :- atom(A).

rule(R_ID) :- head(R_ID, _).

dual(X, neg(X)) :- atom(X).
dual(X, Y) :- dual(Y, X).

active_rule(R_ID) :- head(R_ID, Lit), literal(Lit).

% resolve the choices
L {head((R_ID, Lit), Lit) : choice(C_ID, Lit)} R :- head(R_ID, C_ID), choice_left(C_ID, L), choice_right(C_ID, R).

head((R_ID, Lit'), Lit') :- head(R_ID, C_ID), choice(C_ID, Lit), not head((R_ID, Lit), Lit), dual(Lit, Lit').

body((R_ID, L), Body_Lit) :- head((R_ID, L), L), body(R_ID, Body_Lit).

#program step(t).

% need this for alternation and seminormal step
body(R_ID, L, t) :- body(R_ID, L).

% delete rules according to GL
delete(R_ID, t) :- active_rule(R_ID), body(R_ID, naf(Lit), t), interpretation(Lit, t-1).

% do the GL reduct
reduct_body(R_ID, Lit, t) :- active_rule(R_ID), body(R_ID, Lit, t), explicit_literal(Lit), not delete(R_ID, t), literal(Lit).

% T_p operator
holds_body(R_ID, t) :- not delete(R_ID, t), active_rule(R_ID), interpretation(Lit, t) : reduct_body(R_ID, Lit, t).

% derive head literals:
interpretation(Lit, t):- active_rule(R_ID), holds_body(R_ID, t), head(R_ID, Lit), literal(Lit).

% reach of a fixedpoint
diff(t) :- interpretation(Lit, t), not interpretation(Lit, t-2), t >= 3.
diff(t) :- interpretation(Lit, t-1), not interpretation(Lit, t-3), t >= 3.

% stopping condition becasue of reached fixedpoint
stop(t) :- not diff(t), t >= 3.

% contraddiction
no_model(t) :- interpretation(Lit, t), not interpretation(Lit, t-1), t >= 3, t / 2 = 0.

% stopping condition met because of a contraddiction
stop(t) :- no_model(t).

% output truth values
und(Lit, t)   :- interpretation(Lit, t), not interpretation(Lit, t-1), t >= 3, t / 2 = 1.
true(Lit, t)  :- interpretation(Lit, t-1), t >= 3, t / 2 = 1.
false(Lit, t) :- not interpretation(Lit, t), explicit_literal(Lit), t >= 3, t / 2 = 1.


#program seminormal_step(t).

% do the seminormal pass
body(R_ID, naf(L'), t) :- head(R_ID, L), literal(L), dual(L, L').
