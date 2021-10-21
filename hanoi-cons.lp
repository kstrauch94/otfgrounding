:- move(D,P,T), not blocked(D-1,P,T).
:- move(D,T), on(D,P,T2), blocked(D,P,T), T2 = T-1.
