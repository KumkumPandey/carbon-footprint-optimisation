import random
import math
from typing import List, Dict, Tuple
from geopy.distance import geodesic

class GeneticOptimizer:
    def __init__(self, population_size=50, generations=100, mutation_rate=0.1):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
    
    def optimize_route(self, locations: List[Dict], constraints: Dict) -> Dict:
        """Advanced route optimization using Genetic Algorithm"""
        
        # Create initial population
        population = self._create_initial_population(locations)
        
        best_solution = None
        best_fitness = float('inf')
        
        for generation in range(self.generations):
            # Evaluate fitness for each solution
            fitness_scores = []
            for solution in population:
                fitness = self._calculate_fitness(solution, constraints)
                fitness_scores.append(fitness)
                
                if fitness < best_fitness:
                    best_fitness = fitness
                    best_solution = solution.copy()
            
            # Selection and crossover
            new_population = []
            for _ in range(self.population_size):
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                child = self._crossover(parent1, parent2)
                
                # Mutation
                if random.random() < self.mutation_rate:
                    child = self._mutate(child)
                
                new_population.append(child)
            
            population = new_population
        
        return {
            'optimized_route': best_solution,
            'total_distance': self._calculate_total_distance(best_solution),
            'estimated_time': self._calculate_total_time(best_solution, constraints),
            'carbon_footprint': self._calculate_carbon_footprint(best_solution, constraints),
            'fuel_consumption': self._calculate_fuel_consumption(best_solution, constraints)
        }
    
    def _create_initial_population(self, locations: List[Dict]) -> List[List[Dict]]:
        """Create initial population of route solutions"""
        population = []
        for _ in range(self.population_size):
            route = locations.copy()
            random.shuffle(route)
            population.append(route)
        return population
    
    def _calculate_fitness(self, route: List[Dict], constraints: Dict) -> float:
        """Calculate fitness score (lower is better)"""
        distance = self._calculate_total_distance(route)
        time = self._calculate_total_time(route, constraints)
        carbon = self._calculate_carbon_footprint(route, constraints)
        
        # Weighted fitness function
        fitness = (
            distance * constraints.get('distance_weight', 0.3) +
            time * constraints.get('time_weight', 0.4) +
            carbon * constraints.get('carbon_weight', 0.3)
        )
        return fitness
    
    def _calculate_total_distance(self, route: List[Dict]) -> float:
        """Calculate total distance of route"""
        total_distance = 0
        for i in range(len(route) - 1):
            current = route[i]
            next_loc = route[i + 1]
            distance = geodesic(
                (current['lat'], current['lng']),
                (next_loc['lat'], next_loc['lng'])
            ).kilometers
            total_distance += distance
        return total_distance
    
    def _calculate_total_time(self, route: List[Dict], constraints: Dict) -> float:
        """Calculate total time considering traffic"""
        total_time = 0
        traffic_multiplier = constraints.get('traffic_multiplier', 1.2)
        
        for i in range(len(route) - 1):
            distance = geodesic(
                (route[i]['lat'], route[i]['lng']),
                (route[i + 1]['lat'], route[i + 1]['lng'])
            ).kilometers
            
            # Assume average speed of 60 km/h, adjusted for traffic
            base_time = distance / 60
            adjusted_time = base_time * traffic_multiplier
            total_time += adjusted_time
        
        return total_time
    
    def _calculate_carbon_footprint(self, route: List[Dict], constraints: Dict) -> float:
        """Calculate carbon footprint"""
        distance = self._calculate_total_distance(route)
        load_weight = constraints.get('load_weight', 1000)
        
        # Carbon emission formula (kg CO2 per km)
        base_emission = 0.8  # kg CO2 per km for empty truck
        load_factor = 1 + (load_weight / 10000)  # Additional emission based on load
        
        return distance * base_emission * load_factor
    
    def _calculate_fuel_consumption(self, route: List[Dict], constraints: Dict) -> Dict:
        """Calculate fuel consumption"""
        distance = self._calculate_total_distance(route)
        load_weight = constraints.get('load_weight', 1000)
        
        # Fuel consumption calculation
        base_consumption = 0.25  # liters per km
        load_factor = 1 + (load_weight / 15000)
        
        total_fuel = distance * base_consumption * load_factor
        
        return {
            'diesel': total_fuel * 0.8,  # Assuming 80% diesel
            'petrol': total_fuel * 0.2   # Assuming 20% petrol
        }
    
    def _tournament_selection(self, population: List, fitness_scores: List) -> List[Dict]:
        """Tournament selection for genetic algorithm"""
        tournament_size = 3
        tournament_indices = random.sample(range(len(population)), tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        
        winner_index = tournament_indices[tournament_fitness.index(min(tournament_fitness))]
        return population[winner_index]
    
    def _crossover(self, parent1: List[Dict], parent2: List[Dict]) -> List[Dict]:
        """Order crossover for route optimization"""
        if len(parent1) <= 2:
            return parent1.copy()
        
        start = random.randint(0, len(parent1) - 2)
        end = random.randint(start + 1, len(parent1))
        
        child = [None] * len(parent1)
        child[start:end] = parent1[start:end]
        
        remaining = [item for item in parent2 if item not in child]
        
        j = 0
        for i in range(len(child)):
            if child[i] is None:
                child[i] = remaining[j]
                j += 1
        
        return child
    
    def _mutate(self, route: List[Dict]) -> List[Dict]:
        """Swap mutation for route optimization"""
        if len(route) < 2:
            return route
        
        i, j = random.sample(range(len(route)), 2)
        route[i], route[j] = route[j], route[i]
        return route

class SimulatedAnnealingOptimizer:
    def __init__(self, initial_temp=1000, cooling_rate=0.95, min_temp=1):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
    
    def optimize_route(self, locations: List[Dict], constraints: Dict) -> Dict:
        """Route optimization using Simulated Annealing"""
        current_solution = locations.copy()
        random.shuffle(current_solution)
        
        current_cost = self._calculate_cost(current_solution, constraints)
        best_solution = current_solution.copy()
        best_cost = current_cost
        
        temperature = self.initial_temp
        
        while temperature > self.min_temp:
            # Generate neighbor solution
            neighbor = self._generate_neighbor(current_solution)
            neighbor_cost = self._calculate_cost(neighbor, constraints)
            
            # Accept or reject the neighbor
            if self._accept_solution(current_cost, neighbor_cost, temperature):
                current_solution = neighbor
                current_cost = neighbor_cost
                
                if neighbor_cost < best_cost:
                    best_solution = neighbor.copy()
                    best_cost = neighbor_cost
            
            temperature *= self.cooling_rate
        
        return {
            'optimized_route': best_solution,
            'total_cost': best_cost,
            'total_distance': self._calculate_distance(best_solution),
            'carbon_footprint': self._calculate_carbon(best_solution, constraints)
        }
    
    def _calculate_cost(self, route: List[Dict], constraints: Dict) -> float:
        """Calculate total cost of route"""
        distance = self._calculate_distance(route)
        carbon = self._calculate_carbon(route, constraints)
        return distance + carbon * 10  # Weight carbon emissions
    
    def _calculate_distance(self, route: List[Dict]) -> float:
        """Calculate total distance"""
        total = 0
        for i in range(len(route) - 1):
            total += geodesic(
                (route[i]['lat'], route[i]['lng']),
                (route[i + 1]['lat'], route[i + 1]['lng'])
            ).kilometers
        return total
    
    def _calculate_carbon(self, route: List[Dict], constraints: Dict) -> float:
        """Calculate carbon emissions"""
        distance = self._calculate_distance(route)
        return distance * 0.8 * (1 + constraints.get('load_weight', 1000) / 10000)
    
    def _generate_neighbor(self, route: List[Dict]) -> List[Dict]:
        """Generate neighbor solution by swapping two cities"""
        neighbor = route.copy()
        if len(neighbor) >= 2:
            i, j = random.sample(range(len(neighbor)), 2)
            neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
        return neighbor
    
    def _accept_solution(self, current_cost: float, neighbor_cost: float, temperature: float) -> bool:
        """Decide whether to accept the neighbor solution"""
        if neighbor_cost < current_cost:
            return True
        
        probability = math.exp(-(neighbor_cost - current_cost) / temperature)
        return random.random() < probability