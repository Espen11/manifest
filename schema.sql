drop table if exists users;
create table users (
  user_id integer primary key autoincrement,
	first_name text not null,
	last_name text not null,
  email text not null,
  pw_hash text not null,
	super_user boolean, 
	admin boolean 
);


drop table if exists licenses;
create table licenses (
  id integer primary key autoincrement,
  license varchar
);


drop table if exists planes;
create table planes (
	plane_id integer primary key autoincrement,
	name text not null,
	model text not null
);

drop table if exists loads;
create table loads (
  load_id integer primary key autoincrement,
	plane_id integer,
	day text,
	foreign key(plane_id) references planes(plane_id)
);

drop table if exists slot;
create table slot (
	user_id integer,
	load_id integer,
	foreign key(user_id) references users(user_id),
	foreign key(load_id) references loads(load_id)
);

