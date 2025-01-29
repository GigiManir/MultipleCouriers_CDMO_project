include "globals.mzn";

%INPUT VARIABLES
int: m;  %number of couriers

int: n; %number of items

array [1..m] of int: l; %maximum load size for each courier

array [1..n] of int: s; %size of each item

array [1..n+1, 1..n+1] of int: D; %matrix of distances

%DECISION VARIABLE
int: limit= (ceil(1.5 * n/m)+ 2);
%int: limit = n - m + 2;

array[1..m, 1..limit+1] of var 1..n+1: journeys;  

%We define an array item_bin where item_bin[i] represents the courier (1..m) carrying item i (1..n).
array[1..n] of var 1..m: item_bin; 

%We establish the relatioship between item_bin and journeys
constraint forall(i in 1..m, j in 2..limit where journeys[i, j] != n+1) (
    item_bin[journeys[i, j]] == i
);

constraint forall(k in 1..n) (
    exists(j in 2..limit) (journeys[item_bin[k], j] == k)
);
% Lower bound: minimum distance for a round trip with one item
int: dist_lb = min(i in 1..n) (D[n+1,i] + D[i,n+1]);

% Lower bound for the objective (max single item trip)
int: rho_lb = max(i in 1..n) (D[n+1,i] + D[i,n+1]);

% Upper bound: a complete trip through all items in sequence
int: dist_ub = D[n+1,1] + sum(i in 1..n-1) (D[i,i+1]) + D[n,n+1];
int: rho_ub = dist_ub;

% array containing the total distances of each courrier
array [1..m] of var dist_lb..dist_ub: distances = [sum(j in 1..limit) (D[journeys[i,j], journeys[i,j+1]]) | i in 1..m];

% Objective variable with improved bounds
var rho_lb..rho_ub: z;


% CONSTRAINT
%each courier tour must start and end at the base (n+1)
constraint forall(i in 1..m) (
    journeys[i, 1] == n+1
);

constraint forall(i in 1..m) (
    journeys[i, limit+1] == n+1
);

% Use bin_packing_capa with item_bin
constraint bin_packing_capa(l, item_bin, s);


%if a courier's journey reaches the origin point (n + 1), all subsequent points in the row must also be the origin point. This ensures that once a courier ends its tour, no further deliveries are made.

constraint forall(i in 1..m)(
    forall(j in 2..limit)(
        (journeys[i, j] == n+1) -> forall(k in j+1..limit+1)(journeys[i, k] == n+1)
    )
);

%each courier deliver a package
constraint forall(i in 1..m)(
    exists(j in 2..limit)(journeys[i, j] != n+1)
);

%as we assume that each courier deliver at least one item, each element in the second column must be different from the origin point.
constraint forall (i in 1..m) (journeys[i,2] != n+1);

%each items has to be assigned to a couerier and only once.
constraint alldifferent([journeys[i,j] | i in 1..m, j in 2..limit where journeys[i,j] != n+1]);

% ensures that exactly n packages are assigned to couriers, so every package is carried by someone
%constraint(sum(i in 1..m, j in 2..limit where journeys[i,j] != n+1) (1)) == n;


% ----- SIMMETRY BREAKING CONSTRAINTS -----

% If two couriers have the same capacity then they are symmetric,
% to break the symmetry we impose an order (for the package they pick up) betweem them.
constraint symmetry_breaking_constraint(
    forall(c1 in 1..m, c2 in 1..m where c1 < c2)
     ((l[c1] == l[c2]) -> (lex_less(row(journeys, c1), row(journeys, c2))))
);


z = max(i in 1..m) (distances[i]);

%solve :: int_search(journeys, dom_w_deg, indomain_min)  minimize objective_function;

% Search strategy
solve :: seq_search([
     int_search(journeys, first_fail, indomain_split), 
     int_search(distances, first_fail, indomain_min), 
     int_search(item_bin, first_fail, indomain_split),
    % relax_and_reconstruct(item_bin, 70),
                
  ]) minimize(z) 
