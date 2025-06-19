import random
import time
import subprocess
import os

class VehicleSpawner:
    def __init__(self):
        self.paths = list(range(1, 13))  # 12 paths possíveis
        self.spawn_intervals = (5, 15)  # Entre 5-15 segundos
        
    def spawn_random_vehicles(self):
        """Gera veículos aleatoriamente nos containers existentes"""
        containers = [
            "obu1", "obu2", "obu3", "obu4", "obu5", "obu6", "obu7", "obu8",
            "obu9", "obu10", "obu11", "obu12", "obu13", "obu14", "obu15"
        ]
        
        print("🚗 Iniciando geração aleatória de veículos...")
        
        for container in containers:
            random_path = random.choice(self.paths)
            delay = random.uniform(*self.spawn_intervals)
            
            print(f"📍 {container} -> Path {random_path} (delay: {delay:.1f}s)")
            
            # Reiniciar container com novo path
            try:
                subprocess.run([
                    "docker", "compose", "restart", container
                ], cwd="/home/ricardo/ProjetoRSA")
                
                # Atualizar variável de ambiente
                subprocess.run([
                    "docker", "compose", "exec", container,
                    "sh", "-c", f"export PATH={random_path}"
                ])
                
            except Exception as e:
                print(f"❌ Erro ao configurar {container}: {e}")
            
            time.sleep(delay)
    
    def continuous_spawning(self):
        """Execução contínua com intervalos aleatórios"""
        while True:
            self.spawn_random_vehicles()
            wait_time = random.uniform(60, 120)  # Novo ciclo a cada 1-2 minutos
            print(f"⏰ Próximo ciclo em {wait_time:.0f}s...")
            time.sleep(wait_time)

if __name__ == "__main__":
    spawner = VehicleSpawner()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        spawner.continuous_spawning()
    else:
        spawner.spawn_random_vehicles()