-- docker exec -it hotelprj-container psql -U postgres -d hotelprj to open db
-- \i queries.sql to run queries

-- 1. List all hotels in the Netherlands.
SELECT hotel_name
FROM hotels
Where country = 'Netherlands'
group by hotel_id;

-- 2. Count total bookings per room type.

SELECT room_type_id, count(*) as booking_count
from bookings
group by room_type_id;


-- 3. Find the average satisfaction score per hotel, excluding NULLs.

SELECT
    h.hotel_name,
    COUNT(f.satisfaction_score) AS scored_stays,
    ROUND(AVG(f.satisfaction_score), 2) AS avg_satisfaction
FROM bookings f
JOIN hotels h ON f.hotel_id = h.hotel_id
WHERE f.satisfaction_score IS NOT NULL
GROUP BY h.hotel_id
ORDER BY avg_satisfaction DESC;

-- 4. Find the top 5 highest-spending guests.

select b.guest_id, sum(b.total_revenue) as spent_money, g.first_name, g.last_name
from bookings b
join guests g on b.guest_id = g.guest_id
group by b.guest_id, g.first_name, g.last_name
order by spent_money desc
limit 5;

-- 5. For each hotel, find its highest single booking (by revenue).

Select h.hotel_id, h.hotel_name, max(b.total_revenue) as hotel_revenue
from bookings b
join hotels h on h.hotel_id = b.hotel_id
group by h.hotel_id
order by hotel_revenue desc;


-- 6. Find hotels where more than 2% of bookings are flagged `revenue_mismatch`.

with booking_counts as (
    select hotel_id, count(*) as total_bookings
    from bookings
    group by hotel_id
)

select h.hotel_id, h.hotel_name, count(*) as revenue_mismatch_bookings, bc.total_bookings
from bookings b
join hotels h on h.hotel_id = b.hotel_id
join booking_counts bc on bc.hotel_id = h.hotel_id
where b.data_quality_flag = 'Revenue mismatch'
group by h.hotel_id, h.hotel_name, bc.total_bookings
having count(*) > 0.02 * bc.total_bookings;

-- 7. Rank room types by total revenue using a window function.

select r.room_type_id, r.room_type_name, sum(b.total_revenue) as total_revenure, rank() over (order by sum(b.total_revenue) desc) as revenue_rank
from bookings b
join rooms r on r.room_type_id = b.room_type_id
group by r.room_type_id, r.room_type_name
order by total_revenure desc;


-- 8. Find each guest's first and most recent booking date.

select g.guest_id, g.first_name, g.last_name, min(b.check_in) as first_check_in, max(b.check_in) as last_check_in
from bookings b
join guests g on g.guest_id = b.guest_id
group by g.guest_id, g.first_name, g.last_name
order by first_check_in
limit(5);

-- 9. Calculate month-over-month revenue growth (using `LAG`).

select 
    date_trunc('month', check_in) as booking_month,
    sum(total_revenue) as monthly_revenue,
    LAG(sum(total_revenue)) OVER (ORDER BY date_trunc('month', check_in)) as previous_month_revenue
from bookings
group by date_trunc('month', check_in)
order by booking_month
limit(5);

-- 10. Find guests who have stayed at more than 3 different hotels.

select g.guest_id, g.first_name, g.last_name, count(distinct b.hotel_id) as hotels_stayed
from bookings b
join guests g on g.guest_id = b.guest_id
group by g.guest_id, g.first_name, g.last_name
having count(distinct b.hotel_id) > 3
limit(5);