-- Namu AI - Seed Data

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  age INT NOT NULL,
  goals TEXT[] NOT NULL,
  restrictions TEXT,
  experience_level VARCHAR(50) NOT NULL CHECK (experience_level IN ('iniciante', 'intermediário', 'avançado')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Perfis de usuário variados
INSERT INTO users (name, age, goals, restrictions, experience_level) VALUES
('Ana Costa', 28, ARRAY['reduzir estresse', 'melhorar sono'], 'Nenhuma', 'iniciante'),
('Bruno Lima', 45, ARRAY['perder peso', 'melhorar condicionamento'], 'Problemas no joelho direito, evitar impacto', 'intermediário'),
('Carla Mendes', 35, ARRAY['ganhar flexibilidade', 'reduzir ansiedade'], 'Gestante - 5 meses', 'intermediário'),
('Diego Ferreira', 22, ARRAY['ganhar massa muscular', 'melhorar foco'], 'Intolerância a lactose', 'avançado'),
('Elena Souza', 60, ARRAY['manter mobilidade', 'melhorar equilíbrio', 'reduzir dores'], 'Artrite nas mãos, hipertensão controlada', 'iniciante');
