-- Installs
with installs as (
select
  userId,
  min(dt) as install_date
from
`ppltx-project-dev.PlayPltx.fact`

group by all
)
select
  install_date,
  count(userId) as t_installs
from
  installs
where userId is not null
group by all
order by 1,2
--------------------------
-- DAU
select
  dt,
  count(distinct userId) as DAU
from
`ppltx-project-dev.PlayPltx.fact`
group by all
order by 1 DESC
----------------------------