import time as t
from SAT.src.SAT_utils import *
from constants import *
from utils import *
import z3.z3

class SATsolver:
    def __init__(self, data, output_dir, timeout=300, mode = 'v'):
        self.data = data
        self.output_dir = output_dir
        self.timeout = timeout
        self.solver = Solver()
        self.mode = mode
    
    
    def set_solver(self):
        self.solver = Solver()
        self.solver.set('timeout', self.timeout * 1000)
        
    def solve(self):
        """
            Runs the solver and saves the results:
                - for each data instance
                - for each solving strategy option
                - for each symmetry breaking option
        """
        path = self.output_dir + "/SAT/"
        
        for num, instance in self.data.items():
            json_dict = {}
            print(f"=================INSTANCE {num}=================")
            for strategy, stratstr in STRATEGIES_DICT.items():
                for sym, symstr in SYM_DICT_SAT.items():
                    self.set_solver()
                    
                    variables = self.set_constraints(instance, strategy)
                    
                    if sym == SYMMETRY_BREAKING:
                        self.add_sb_constraints(instance, variables)

                    if sym == HEURISTICS:
                        self.add_heu_constraints(instance, variables)

                    time, optimal, obj, sol = self.optimize(instance, strategy, variables)
                    
                    print(f"Max distance found using {stratstr} search", end= "")
                    if sym==NO_SYMMETRY_BREAKING: print(' :      ', end= "")
                    elif sym==SYMMETRY_BREAKING:  print('  w sb: ', end= "")
                    else:                         print(' no heu:', end= "")
                    print(obj)
                    
                    key_dict = stratstr + symstr
                    json_dict[key_dict] = {"time" : time, "optimal": optimal, "obj": obj, "sol": sol}
                    if self.mode == 'v':
                        print()
                if self.mode == 'v':
                    print()
            print()

            save_file(path, num + ".json", json_dict)
        
    def optimize(self, instance, strategy, variables):   
        """
            Calls the search functions depending on the strategy selected.
            :return
                time: time needed to solve the instance
                optimal: True if the solution is optimal
                obj: objective function of the best solution found
                sol: list of the paths of each courier in the best solution
        """
        if strategy == LINEAR_SEARCH:
            time, optimal, obj, sol = self.linear_search(instance, variables)
        elif strategy == BINARY_SEARCH:
            time, optimal, obj, sol = self.binary_search(instance, variables)
        
        return time, optimal, obj, sol
    
    def linear_search(self, instance, variables):
        """
            Runs linear search
            :return
                time: time needed to solve the instance
                optimal: True if the solution is optimal
                obj: objective function of the best solution found
                sol: list of the paths of each courier in the best solution
        """
        rho, X, D_tot, _ = variables
        m,n,_,_,D = instance.unpack()
        maxDistBin= int(np.ceil(np.log2(instance.courier_dist_ub)))
        
        start_time = t.time()        
        iter = 0
        
        previousModel = None
        satisfiable = True
        optimal = True

        self.solver.push()
        #search for a statifiable solution 
        while(satisfiable):
            status = self.solver.check()
            if status == sat:
                iter += 1
                model = self.solver.model()
                previousModel = model
            
                current_time = t.time()
            
                past_time = int((current_time - start_time))
                self.solver.set('timeout', (self.timeout - past_time)*1000)
                
                dist = [model.evaluate(rho[b]) for b in range(maxDistBin)]
                self.solver.add(Not(lesseq(dist, rho)))
                
                
            elif status == unsat:
                if iter == 0:
                    print("UNSAT")
                    past_time = int((current_time - start_time))
                    return past_time, False, "N/A", []
                satisfiable = False

            elif status == unknown:
                if iter == 0:
                    print("UNKNOWN RESULT for insufficient time")
                    return self.timeout, False, "N/A", []
                elif self.mode == 'v':
                    print(f"The computation time exceeded the limit ({self.timeout} seconds)")
                satisfiable = False
                optimal = False
                
        current_time = t.time()
        past_time = current_time - start_time

        model = previousModel            
        x = [[[ model.evaluate(X[i][j][k]) for k in range(0,n+1) ] for j in range(n) ] for i in range(m)]
        xDD = [[model.evaluate(D_tot[i][b]) for b in range(maxDistBin)] for i in range(m)]
        
        distances = [toInteger(np.array(xDD[i])) for i in range(m)]
        obj = max(distances)
        
        tot_s = []
        for i in range(m):
            sol = []
            for j in range(n):
                for k in range(1,n+1):
                    if x[i][j][k] == True:
                        sol.append(k)
            tot_s.append(sol)

        distances,tot_s = instance.post_process_instance(distances,tot_s)
        
        if self.mode == 'v':
            print("Time from beginning of the computation:", np.round(past_time, 2), "seconds")
            
            print("Solution:")
            for i in range(m):
                print(f"Courier {i+1}:","deposit => ", end = "")
                for s in tot_s[i]:
                    print(s,"=> ", end = "")
                print("deposit")
            print("Distance travelled:")
            for i in range(m):
                print(f"Courier {i+1}: ", toInteger(np.array(xDD[i])))
        

        return int(past_time), optimal, obj, tot_s
        
        
    def binary_search(self, instance, variables):
        """
            Runs binary search
            :return
                time: time needed to solve the instance
                optimal: True if the solution is optimal
                obj: objective function of the best solution found
                sol: list of the paths of each courier in the best solution
        """
        rho, X, D_tot, _ = variables
        m,n,_,_,D = instance.unpack()
        maxDistBin= int(np.ceil(np.log2(instance.courier_dist_ub)))
        maxDist = instance.courier_dist_ub
        
        UPPER_BOUND = maxDist
        LOWER_BOUND = np.max(D[-1] + D[:,-1])
        
        self.solver.set('timeout', self.timeout * 1000)

        start_time = t.time()
        iter = 0
        
        satisfiable = True
        optimal = True
        previousModel = None
        
        while(satisfiable):
            if (UPPER_BOUND - LOWER_BOUND) <= 1:
                if self.mode == 'v':
                    print(f"UPPER={UPPER_BOUND}, LOWER= {LOWER_BOUND}: last search")
                satisfiable = False
            
            if UPPER_BOUND - LOWER_BOUND == 1:
                MIDDLE_BOUND = LOWER_BOUND
            else:
                MIDDLE_BOUND = int(np.ceil((UPPER_BOUND + LOWER_BOUND) / 2))
            middle_bits = toBinary(MIDDLE_BOUND, maxDistBin, BoolVal)  # notice the +0
            
            self.solver.add(lesseq(rho, middle_bits))
            if self.mode == 'v':
                print(f"search inside [{LOWER_BOUND}-{MIDDLE_BOUND}]: ", end= "")    
            
            current_time = t.time()
            past_time = int(current_time - start_time)
            self.solver.set('timeout', (self.timeout - past_time)*1000)
            
            status = self.solver.check()
            
            if self.mode == 'v':
                print(status, end= ("" if status == sat else "\n"))
                
            if status == sat:
                iter += 1
                model = self.solver.model()
                previousModel = model
                dist = [model.evaluate(rho[b]) for b in range(maxDistBin)]
                if self.mode == 'v':
                    print(" obj: ", toInteger(dist))
                UPPER_BOUND = toInteger(dist)

            elif status == unsat:
                if iter == 0:
                    print("UNSAT")
                    past_time = int((current_time - start_time))
                    return past_time, False, "N/A", []
                iter += 1
                self.solver.pop()
                self.solver.push()
                LOWER_BOUND = MIDDLE_BOUND
            
            elif status == unknown:
                if iter == 0:
                    print("UNKNOWN RESULT for insufficient time")
                    return self.timeout, False, "N/A", []
                elif self.mode == 'v':
                    print(f"The computation time exceeded the limit ({self.timeout} seconds)")      
                satisfiable = False
                optimal = False
            
        
        current_time = t.time()
        past_time = current_time - start_time

        model = previousModel
        x = [[[ model.evaluate(X[i][j][k]) for k in range(0,n+1) ] for j in range(n) ] for i in range(m)]
        xDist = [[model.evaluate(D_tot[i][b]) for b in range(maxDistBin)] for i in range(m)]
        distances = [toInteger(np.array(xDist[i])) for i in range(m)]
        obj = max(distances)
        # output  
        tot_s = []
        for i in range(m):
            sol = []
            for j in range(n):
                for k in range(1,n+1):
                    if x[i][j][k] == True:
                        sol.append(k)
            tot_s.append(sol)

        distances,tot_s = instance.post_process_instance(distances, tot_s)
        
        if self.mode == 'v':
            print("Time from beginning of the computation:", np.round(past_time, 2), "seconds")
            print("Solution:")
            for i in range(m):
                print(f"Courier {i+1}:","deposit => ", end = "")
                for s in tot_s[i]:
                    print(s,"=> ", end = "")
                print("deposit")
            print("Distance travelled:")
            for i in range(m):
                print(f"Courier {i+1}: ", toInteger(np.array(xDist[i])))

        return int(past_time), optimal, obj, tot_s
    
    
    def set_constraints(self, instance, strategy):
        """
            Adds constraints to the solver and pushes them
        """
        m, n, s, l, D = instance.unpack()

        maxD = np.max(instance.D)
        #mins = instance.courier_min_load
        maxDBin = int(np.ceil(np.log2(maxD)))
        maxDist = instance.courier_dist_ub
        maxDistBin = int(np.ceil(np.log2(maxDist)))
        maxWeight = instance.courier_max_load
        maxWeightBin = int(np.ceil(np.log2(maxWeight)))
        maxDBin = maxDistBin
        
        X = [[[Bool(f"x_{i}_{j}_{k}") for k in range(0,n+1)] for j in range(n)] for i in range(m)]

        # binary-encodes the input variables
        l = [[BoolVal(b) for b in toBinary(l[i], length = maxWeightBin)] for i in range(m)]
        s = [[BoolVal(b) for b in toBinary(s[j], length = maxWeightBin)] for j in range(n)]
        D = [[[BoolVal(b) for b in toBinary(D[i][j], length = maxDBin)] for j in range(n+1)] for i in range(n+1)]
        #mins = [BoolVal(b) for b in toBinary(mins,length = maxWeightBin)]
        
        # each cell has only one value.
        for i in range(m):
            for j in range(n):
                self.solver.add(exactly_one(X[i][j], f"valid_cell_{i}_{j}"))

        # each element except zero should be seen only once inside the matrix
        for k in range(1,n+1):
            self.solver.add(exactly_one([X[i][j][k] for i in range(m) for j in range(n)],f"valid_k{k}"))

        # ordering constraint: if the courier does not take the kth pack at position j, also at position j+1 doesnt
        for i in range(m):
            for j in range(n-1):
                self.solver.add(Implies(X[i][j][0], X[i][j+1][0]))
        
        # all start
        for i in range(m):
            self.solver.add(at_least_one([X[i][0][k] for k in range(1,n+1)]))

        # each courier can only deliver items whose total size doesn't exceed limit
        W_par = [[[Bool(f"partial_weight_{i}_{k}_{b}") for b in range(maxWeightBin)] for k in range(n)] for i in range(m)]
        W_tot = [[Bool(f"total_weight_{i}_{b}") for b in range(maxWeightBin)] for i in range(m)]

        for i in range(m):
            # 1. copy the weight from s to partial weight if needed
            for k in range(n):
                self.solver.add( Implies( at_least_one([X[i][j][k+1] for j in range(n)]), And([W_par[i][k][b] == s[k][b] for b in range(maxWeightBin)])))
                self.solver.add( Implies( Not(at_least_one([X[i][j][k+1] for j in range(n)])), And([Not(W_par[i][k][b]) for b in range(maxWeightBin)])))
            # 2. compute the sum of the partial weights for each courier
            self.solver.add(sum_vec(W_par[i], W_tot[i], name= f"weight_{i}"))
            # 3. for each courier the sum must be less than or equal to the max load size
            self.solver.add(lesseq(W_tot[i], l[i]))
            #self.solver.add(lesseq(mins,W_tot[i]))

        D_par = [[[Bool(f"partial_distances_{i}_{j}_{b}") for b in range(maxDBin)] for j in range(n+1)] for i in range(m)]
        D_tot = [[ Bool(f"total_distances_{i}_{b}") for b in range(maxDistBin)] for i in range(m)]
        
        rho = [Bool(f"obj_{b}") for b in range(maxDistBin)]

        # 1. copy the distances from D to partial distances if needed
        for i in range(m):
            # from deposit to first place
            self.solver.add(Implies(X[i][0][0], And([Not(D_par[i][j][b]) for j in range(n+1) for b in range(maxDBin)])))
            
            for k in range(1, n+1):
                self.solver.add(Implies(Not(X[i][0][0]), Implies(X[i][0][k], equals(D_par[i][0], D[n][k-1]))))
            
            # from j - 1 to j
            for j in range(1, n):
                for k1 in range(1, n+1):
                    for k2 in range(1, n+1):
                        self.solver.add(Implies(Not(X[i][0][0]), Implies(And(X[i][j-1][k1], X[i][j][k2]), equals(D_par[i][j], D[k1-1][k2-1]))))     

                    self.solver.add(Implies(Not(X[i][0][0]), Implies(And(X[i][j-1][k1], Not(at_least_one(X[i][j][1:]))), equals(D_par[i][j], D[k1-1][n]))))
                self.solver.add(Implies(Not(X[i][0][0]), Implies(And(X[i][j-1][0], X[i][j][0]), equals(D_par[i][j], D[n][n]))))

            for k in range(1, n+1):
                self.solver.add(Implies(X[i][-1][k], equals(D_par[i][-1], D[k-1][n])))

            self.solver.add(Implies(X[i][-1][0], equals(D_par[i][-1], D[n][n]))) # se il corriere non porta pacchi nell'istante j allora copia 0 nelle distanze
        
            # 2. compute the sum of the distances for each courier
            self.solver.add(sum_vec(D_par[i], D_tot[i], name = f"dist_{i}"))

        if strategy == LINEAR_SEARCH:
            for i in range(m):
                self.solver.add(lesseq(D_tot[i], rho))

        elif strategy == BINARY_SEARCH:
            self.solver.add(maximum(D_tot,rho))

        self.solver.push()

        return rho, X, D_tot, W_tot
        

    def add_sb_constraints(self, instance, variables):
        """
            Inserts the additional symmetry breaking constraints to the solver and pushes them
        """
        m, _, _, l, _ = instance.unpack()
        _, X, _, W_tot = variables
        # lexicographic ordering between the paths of two couriers with same load capacity
        # se un corriere ha più capacity lo forziamo a depositare più carico
        for i in range(m - 1):
            if l[i] == l[i+1]:
                self.solver.add(ohe_less(X[i][0], X[i+1][0]))
            else: # l[i] > l[i+1]
                self.solver.add(lesseq(W_tot[i+1], W_tot[i]))

        self.solver.push()

    def add_heu_constraints(self, instance, variables):
        """
            Inserts additional heuristic constraints to the solver and pushes them
        """
        m, n, _, _, _ = instance.unpack()
        _, X, _, _ = variables

        # only the first couriers (those with the most capacity) carry the most items
        for i in range(m - 1):
            for j in range(n):
                self.solver.add(Implies(X[i][j][0], X[i+1][j][0]))
        
        self.solver.push()