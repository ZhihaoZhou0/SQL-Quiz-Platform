CREATE TABLE IF NOT EXISTS restaurants (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  address TEXT,
  distance_miles NUMERIC,
  rating NUMERIC,
  cuisine TEXT,
  avg_cost NUMERIC,
  personal_rank INT
);

INSERT INTO restaurants (name, address, distance_miles, rating, cuisine, avg_cost, personal_rank) VALUES
('NuvoTaco', '2512 University Dr, Durham, NC 27707', 1.2, 4.8, 'Mexican', 12.50, 3),
('Pizzeria Toro', '105 E Chapel Hill St, Durham, NC 27701', 1.8, 4.5, 'Italian', 18.00, 4),
('Bullock''s BBQ', '3330 Quebec Dr, Durham, NC 27705', 2.1, 4.4, 'Southern/BBQ', 15.00, 5),
('Guglhupf Bakery', '2706 Durham-Chapel Hill Blvd, Durham, NC 27707', 1.9, 4.6, 'German Cafe', 20.00, 6),
('M Sushi', '311 Holland St, Durham, NC 27701', 2.2, 4.7, 'Japanese', 35.00, 1),
('Sushi Love', '2812 Erwin Rd #204, Durham, NC 27705', 0.6, 4.1, 'Japanese', 25.00, 2);