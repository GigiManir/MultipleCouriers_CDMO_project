include "globals.mzn";

%INPUT VARIABLES
int: m;

int: n;

array [1..m] of int: l;

array [1..n] of int: s;

array [1..n+1, 1..n+1] of int: D;

%DECISION VARIABLE
int: limit = n - m + 2;

array[1..m, 1..limit+1] of var 1..n+1: journeys;    

array [1..m] of var int: weight = [sum(j in 2..limit where journeys[i,j] != n+1) (s[journeys[i,j]]) | i in 1..m];

% array containing the total distances of each courrier
array [1..m] of var int: distances = [sum(j in 1..limit) (D[journeys[i,j], journeys[i,j+1]]) | i in 1..m];


% Distance bounds
int: dist_lb = min(i in 1..n) (D[n+1,i] + D[i,n+1]);  % Lower bound for distance
int: dist_ub = D[n+1,1] + sum(i in 1..n) (D[i,i+1]);  % Upper bound for distance


var dist_lb..dist_ub: z;

%CONSTRAINTS

constraint alldifferent([journeys[i,j] | i in 1..m, j in 2..limit where journeys[i,j] != n+1]);

% ensures that exactly n packages are assigned to couriers, so every package is carried by someone
constraint(sum(i in 1..m, j in 2..limit where journeys[i,j] != n+1) (1)) == n;

% Each courier can carry a weight less than the maximum load they can suppor
constraint forall(i in 1..m) (
    weight[i] <= l[i]
);

set of int: nmax_among = n+1..n+1;

% in the first column of journeys all m rows must have n+1 (the base)
constraint among(m, col(journeys, 1), nmax_among);

% in the last column of journeys all m rows must have n+1 (the base)
constraint among(m, col(journeys, limit+1), nmax_among);


constraint among(0, col(journeys, 2), nmax_among);

%using this constraint we impose that the courier cannot return until he has finished delivering
constraint forall(i in 1..m)(
    forall(j in 3..limit)((journeys[i,j] == n+1) -> not exists(k in j..limit)(journeys[i,k] != n+1))
);

% ----- SIMMETRY BREAKING CONSTRAINTS -----

% If two couriers have the same capacity then they are symmetric,
% to break the symmetry we impose an order (for the package they pick up) betweem them.
constraint symmetry_breaking_constraint(
    forall(c1 in 1..m, c2 in 1..m where c1 < c2)
     ((l[c1] == l[c2]) -> (lex_less(row(journeys, c1), row(journeys, c2))))
);

% Two couriers path are exchangeable if the maximum weight of the two is less than the minimum loading capacity
% in that case we impose an ordering between them

constraint symmetry_breaking_constraint(
    forall(c1 in 1..m, c2 in 1..m where c1 < c2)
    (
      (max(weight[c1], weight[c2]) <= min(l[c1], l[c2])) ->
      (lex_less(row(journeys, c1), row(journeys, c2))))
);


% Comment if couriers can go back to base before taking other packages
constraint forall(i in 1..m)(
    forall(j in 3..limit)((journeys[i,j] == n+1) -> not exists(k in j..limit)(journeys[i,k] != n+1))
);

% If a courier can take a package, he will
constraint forall(c1 in 1..m)
  (
  (l[c1] >= max(s)) -> exists(k in 1..limit)(journeys[c1,k] != n+1));

z = max(i in 1..m) (distances[i]);

%solve :: int_search(journeys, dom_w_deg, indomain_min)  minimize objective_function;

% Search strategy
solve :: seq_search([
    int_search(journeys, first_fail, indomain_split),
    
    int_search(distances, first_fail, indomain_split),
    restart_luby(10)
]) minimize(z);
