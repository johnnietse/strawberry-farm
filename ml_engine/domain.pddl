(define (domain phytotron-maintenance)
  (:requirements :strips :typing :equality)
  (:types node location technician)

  (:predicates
    (at ?obj - (either node technician) ?loc - location)
    (calibrated ?n - node)
    (battery-low ?n - node)
    (charged ?n - node)
    (connected ?l1 ?l2 - location)
  )

  ;; Technician moves between greenhouse rows
  (:action move
    :parameters (?t - technician ?from ?to - location)
    :precondition (and (at ?t ?from) (connected ?from ?to))
    :effect (and (not (at ?t ?from)) (at ?t ?to))
  )

  ;; Technician calibrates a node (e.g., pH/EC sensors)
  (:action calibrate-sensor
    :parameters (?t - technician ?n - node ?loc - location)
    :precondition (and (at ?t ?loc) (at ?n ?loc))
    :effect (calibrated ?n)
  )

  ;; Technician replaces/charges battery (Dr. Pahlevani's WPT could automate this)
  (:action replace-battery
    :parameters (?t - technician ?n - node ?loc - location)
    :precondition (and (at ?t ?loc) (at ?n ?loc) (battery-low ?n))
    :effect (and (not (battery-low ?n)) (charged ?n))
  )
)
