literal(A)                :- atom(A).
literal(neg(A))           :- atom(A).
literal(naf(A))           :- atom(A).
literal(naf(neg(A)))      :- atom(A).
explicit_literal(A)       :- atom(A).
explicit_literal(neg(A))  :- atom(A).
atom(A)                   :- atoms(A).

rule(R_ID) :- head(R_ID, _).

dual(X, neg(X)) :- atom(X).
dual(X, Y) :- dual(Y, X).

choice_resolved_rule(R_ID) :- head(R_ID, Lit), literal(Lit).

% resolve the choices
L {head(choice_resolved(R_ID), Lit) : choice(C_ID, Lit)} R :- head(R_ID, C_ID), choice_left(C_ID, L), choice_right(C_ID, R).

head(choice_resolved(R_ID), Lit') :- head(R_ID, C_ID), choice(C_ID, Lit), not head(choice_resolved(R_ID), Lit), dual(Lit, Lit').

body(choice_resolved(R_ID), Body_Lit) :- head(choice_resolved(R_ID), L), body(R_ID, Body_Lit).

#program step(t).

% need this for alternation and seminormal step
body(R_ID, L, t) :- body(R_ID, L), choice_resolved_rule(R_ID).

% delete rules according to GL
delete(R_ID, t) :- choice_resolved_rule(R_ID), body(R_ID, naf(Lit), t), interpretation(Lit, t-1).

% do the GL reduct
reduct_body(R_ID, Lit, t) :- choice_resolved_rule(R_ID), body(R_ID, Lit, t), explicit_literal(Lit), not delete(R_ID, t), literal(Lit).

% T_p operator
holds_body(R_ID, t) :- not delete(R_ID, t), choice_resolved_rule(R_ID), interpretation(Lit, t) : reduct_body(R_ID, Lit, t).

% derive head literals:
interpretation(Lit, t):- choice_resolved_rule(R_ID), holds_body(R_ID, t), head(R_ID, Lit), literal(Lit).

% reach of a fixed-point
diff(t) :- interpretation(Lit, t), not interpretation(Lit, t-2), t >= 3.
diff(t) :- interpretation(Lit, t-1), not interpretation(Lit, t-3), t >= 3.
diff(t) :- not interpretation(Lit, t), interpretation(Lit, t-2), t >= 3.
diff(t) :- not interpretation(Lit, t-1), interpretation(Lit, t-3), t >= 3.

% stopping condition becasue of reached fixedpoint
stop(t) :- not diff(t), t >= 3, t \ 2 = 1.

% contraddiction
no_model(t) :- interpretation(Lit, t-1), not interpretation(Lit, t), t >= 3, t \ 2 = 1. % t conservative, as t mod 2 == 0, and t-1 optimistic

% stopping condition met because of a contraddiction
stop(t) :- no_model(t), t \ 2 = 1.


% output truth values
und(Lit, t)   :- interpretation(Lit, t), not interpretation(Lit, t-1).
true(Lit, t)  :- interpretation(Lit, t-1).
false(Lit, t) :- not interpretation(Lit, t), explicit_literal(Lit).

no_model(t, is_undefined(Lit)) :- not_undefined(Lit), stop(t), t >= 3, t \ 2 = 1, und(Lit, t).

%no_model(t, is_not_undefined(Lit)) 
:- undefined(Lit), t >= 3, t==5, not und(Lit, t), t \ 2 = 1.

#program seminormal_step(t).

% do the seminormal pass
body(R_ID, naf(L'), t) :- choice_resolved_rule(R_ID), head(R_ID, L), literal(L), dual(L, L').
