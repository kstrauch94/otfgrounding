block(1..3).
loc(L) :- block(L).
loc(table).

init(on(1,2)).
init(on(2,3)).
init(on(3,table)).

goal(on(1,table)).
goal(on(2,1)).
goal(on(3,2)).