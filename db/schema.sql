\set version 7  -- if you change this file, increment me!
create table version (version integer not null);
insert into version values (:version);

create table temperatures (
    id serial primary key,
    hub_id text not null check (hub_id != ''),
    cell_id text not null check (cell_id != ''),

    -- new firmware sends adc, old firmware sends temperature:
    adc integer,
    temperature real,
    humidity real,
    constraint adc_or_temperature check ((adc is null) != (temperature is null)),

    sleep_period integer not null,
    relay boolean not null,
    hub_time timestamp with time zone not null,
    time timestamp with time zone not null default now(),
    relayed_time timestamp with time zone
);
create index on temperatures (hub_id, time desc);
create index on temperatures (cell_id, time desc);

create table hubs (
    id serial primary key,
    hub_id text not null check (hub_id != ''),
    pi_id text not null check (pi_id != ''),
    sleep_period integer not null,

    -- always present in newer firmwares, but absent in older ones:
    disk_free integer,
    uptime real,
    version text check (version != ''),

    port integer, -- optional

    time timestamp with time zone not null default now()
);
create index on hubs (hub_id, time desc);

create table cells (
    id text unique not null check (id != ''),
    version text not null check (version != '')
);

create table xbees (
    id text unique not null check (id != ''),
    short_id text unique not null check (short_id != '')
);

create table commands (
    id serial primary key,
    hub_id text not null check (hub_id != ''),
    action text not null,
    params text,
    created_at timestamp with time zone not null default now()
);
create index on commands (hub_id, created_at);
