-- Sources (optional, useful metadata)
create table if not exists sources (
  id bigserial primary key,
  name text not null unique,
  base_url text
);

-- Asset registry: one row per asset (crypto, etc.)
create table if not exists assets (
  id bigserial primary key,
  symbol text not null,          -- BTC, ETH
  name   text not null,          -- Bitcoin, Ethereum
  cg_id  text not null,          -- coingecko coin id, e.g. 'bitcoin'
  unique(symbol),
  unique(cg_id)
);

-- Quote currencies (fiat/crypto used as quote)
create table if not exists quotes (
  id bigserial primary key,
  code text not null unique,     -- USD, GBP, EUR
  name text not null,
  decimals int not null default 2
);

-- Daily close prices (write-through cache)
create table if not exists asset_quotes (
  id bigserial primary key,
  asset_id bigint not null references assets(id) on delete cascade,
  quote_id bigint not null references quotes(id) on delete cascade,
  ts date not null,
  price numeric not null,
  source text not null default 'coingecko',
  inserted_at timestamptz not null default now(),
  unique(asset_id, quote_id, ts)
);
