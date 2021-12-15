% a block can’t be moved unless it is clear
:- move(B,L,T), on(B1,B,T), isfact_block(B), isfact_block(B1), isfact_location(L), isfact_time(T), T<horizon.

% a block can’t be moved onto a block that is being moved also

:- move(B,B1,T), move(B1,L,T), isfact_block(B), isfact_block(B1), isfact_location(L), isfact_time(T), T<horizon, grippers > 1.
