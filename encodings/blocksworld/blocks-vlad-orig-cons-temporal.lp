% a block can’t be moved unless it is clear
:- temporal_move(B,L,T), temporal_on(B1,B,T), isfact_block(B), isfact_block(B1), isfact_location(L), isfact_time(T), T<horizon.

% a block can’t be moved onto a block that is being moved also

:- temporal_move(B,B1,T), temporal_move(B1,L,T), isfact_block(B), isfact_block(B1), isfact_location(L), isfact_time(T), T<horizon, grippers > 1.
