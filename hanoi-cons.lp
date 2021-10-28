:- move(D,P,T), blocked(D2,P,T), D2 = D - 1.
:- move(D,T), on(D,P,T2), blocked(D,P,T), T2 = T-1.