

@Component()
class Mover:
    """
    A moving entity.

    :param Vec3 move: (0, 0, 0) - speed of relative movement
    :param float heading: 0.0 - horizontal direction the mover is headed
    :param float pitch: 0.0 - vertical direction the mover is headed

    Remaining variables are calculated by systems.
    """

    # Input or AI
    move: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    heading: float = 0.0
    pitch: float = 0.0
    # FIXME: Shouldn't be used anymore
    max_heading: float = 90.0
    max_pitch: float = 90.0
    # Intention of movement
    translation: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    rotation: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    clamp_pitch: bool = True
    # Speed bookkeeping
    last_translation_speed: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    last_rotation_speed: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    # Gravity vector
    gravity: Vec3 = field(default_factory=lambda: Vec3(0, 0, -1))


@Component()
class FloatingMovement:
    '''
    This mover floats, moves with 6 degrees of freedom.

    :param float speed: 200.0 - speed of relative forward movement
    :param float turning_speed: 60.0 - rotation speed
    '''
    speed: float = 200.0
    turning_speed: float = 60.0


@Component()
class InertialMovement:
    '''
    This movement is smooth.

    :param float acceleration: 30.0 - rate at which to accumulate speed
    :param float rotated_inertia: 0.5 - how much rotation impacts inertia
    :param NodePath node: NodePath("Inertia") - relative position based on inertia
    :param bool ignore_z: True - ignore_z
    :param bool delta_inputs: False - Inputs in the mover indicate a wish for change in speed, not absolute speed
    '''
    acceleration: float = 30.0
    rotated_inertia: float = 0.5
    node: NodePath = field(default_factory=lambda: NodePath("Inertia"))
    ignore_z: bool = True
    delta_inputs: bool = False


@Component()
class BumpingMovement:
    '''
    This mover's horizontal movement is hindered by collisions.
    '''
    tag_name: str = 'bumping'
    from_collide_mask: int = BUMPING_MASK
    into_collide_mask: int = BUMPING_MASK
    # The name of the node to use if `solids` is None
    node_name: str = 'bumper'
    solids: dict = None  # field(default_factory=lambda: dict())
    contacts: list = field(default_factory=list)
    traverser: CollisionTraverser = field(default_factory=CollisionTraverser)
    queue: CollisionHandlerQueue = field(default_factory=CollisionHandlerPusher)
    debug: bool = False



# Movement systems
#
# These systems modify the intended movement as stored on the
# mover controller to conform to external constraints. A
# recurring element is that systems will run a collision
# traverser, so first we provide a helpful base class.
class CollisionSystem(System):
    proxies = {
        'mover_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
    }

    def init_sensors(self, entity, movement):
        solids = movement.solids
        if solids is not None:  # Create solids from specification
            for tag, solid in solids.items():
                solid['tag'] = tag
                if solid['shape'] is CollisionSphere:
                    shape = CollisionSphere(solid['center'], solid['radius'])
                    self.add_shape(entity, movement, solid, shape)
                elif solid['shape'] is CollisionCapsule:
                    shape = CollisionCapsule(
                        solid['end_a'],
                        solid['end_b'],
                        solid['radius'],
                    )
                    self.add_shape(entity, movement, solid, shape)
        else:  # Fetch solids from model
            model_node = self.proxies['mover_node'].field(entity)
            solids = model_node.find_all_matches(
                f'**/{movement.node_name}',
            )
            print(solids)
            for nodepath in solids:
                # FIXME: Colliding with multiple nodes is broken. See
                # bumping and Falling as well.
                movement.solids = {movement.node_name: {'node': nodepath}}
                # FIXME: This is mostly copypasta from add_solid, which
                # should be broken up.
                node = nodepath.node()
                #import pdb; pdb.set_trace()
                node.set_from_collide_mask(movement.from_collide_mask)
                node.set_into_collide_mask(movement.into_collide_mask)
                movement.traverser.add_collider(
                    nodepath,
                    movement.queue,
                )
                node.set_python_tag(movement.tag_name, movement)
                if movement.debug:
                    nodepath.show()

        if movement.debug:
            scene_proxy = self.proxies['scene_node']
            scene = entity[scene_proxy.component_type]
            scene_node = scene_proxy.field(entity)

            movement.traverser.show_collisions(scene_node)

    def add_shape(self, entity, movement, solid, shape):
        model_proxy = self.proxies['mover_node']
        model = entity[model_proxy.component_type]
        model_node = model_proxy.field(entity)

        node = NodePath(
            CollisionNode(
                f'{movement.tag_name}-{solid["tag"]}',
            ),
        )
        solid['node'] = node
        node.node().add_solid(shape)
        node.node().set_from_collide_mask(movement.from_collide_mask)
        node.node().set_into_collide_mask(movement.into_collide_mask)
        node.reparent_to(model_node)
        movement.traverser.add_collider(node, movement.queue)
        node.set_python_tag(movement.tag_name, movement)
        if 'debug' in solid and solid['debug']:
            node.show()

    def run_sensors(self, entity, movement):
        scene_proxy = self.proxies['scene_node']
        scene = entity[scene_proxy.component_type]
        scene_node = scene_proxy.field(entity)

        movement.traverser.traverse(scene_node)
        movement.queue.sort_entries()
        movement.contacts = movement.queue.entries


@Component()
class FrictionalMovement:
    '''
    A slow-down is applied to the mover.
    '''
    half_life: float = 5.0



# @Component()
# class MovementSensors:
#     solids: dict = field(default_factory=lambda:dict())
#     contacts: dict = field(default_factory=lambda:dict())
#     traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser())
#     queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
#     debug: bool = False


class Floating(System):
    '''
        Components used :func:`wecs.core.and_filter` 'mover'
            | :class:`wecs.panda3d.mover.Mover`
            | :class:`wecs.panda3d.mover.FloatingMovement`
    '''
    entity_filters = {
        'mover': and_filter([
            Mover,
            FloatingMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['mover']:
            mover = entity[Mover]
            floating = entity[FloatingMovement]

            mover.translation *= floating.speed
            mover.rotation *= floating.turning_speed



class Inertiing(System):
    '''
        Accelerate mover, as opposed to an instantanious velocity.

        Components used :func:`wecs.core.and_filter` 'mover'
            | :class:`wecs.panda3d.mover.InertialMovement`
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.model.clock`
    '''
    entity_filters = {
        'mover': and_filter([
            Proxy('mover_node'),
            Clock,
            Mover,
            InertialMovement,
        ]),
    }
    proxies = {'mover_node': ProxyType(Model, 'node')}

    def enter_filter_mover(self, entity):
        movement = entity[InertialMovement]
        model_proxy = self.proxies['mover_node']
        model = entity[model_proxy.component_type]
        model_node = model_proxy.field(entity)

        movement.node.reparent_to(model_node)
        movement.node.set_hpr(0, 0, 0)

    def exit_filter_mover(self, entity):
        # detach InertialMovement.node
        import pdb;
        pdb.set_trace()

    def update(self, entities_by_filter):
        for entity in entities_by_filter['mover']:
            dt = entity[Clock].game_time
            model_proxy = self.proxies['mover_node']
            model = entity[model_proxy.component_type]
            model_node = model_proxy.field(entity)
            mover = entity[Mover]
            inertia = entity[InertialMovement]

            # Usually you want to apply inertia only to x and y, and
            # ignore z, so we cache it.
            old_z = mover.translation.z

            # We use inertia.node to represent "last frame's" model
            # orientation, scaled for how much inertia you'd like to
            # keep model-relative. Wow, what a sentence...
            # When you run forward and turn around, where should inertia
            # carry you? Physically, towards your new backward
            # direction. The opposite end of the scale of realism is
            # that your inertia vector turns around with you, and keeps
            # carrying you towards your new forward.
            # So if inertia.rotated_inertia = 1.0, inertia.node will
            # be aligned with the model, and thus the inertia vector
            # turns with you. If inertia.rotated_inertia = 0.0,
            # inertia.node will extrapolate the model's past rotation,
            # and the inertia vector will thus be kept still relative to
            # the surroundings. And if it is between those, it will
            # interpolate accordingly.
            inertia.node.set_hpr(
                -mover.last_rotation_speed * dt * (1 - inertia.rotated_inertia),
            )
            last_speed_vector = model_node.get_relative_vector(
                inertia.node,
                mover.last_translation_speed,
            )

            # Now we calculate the wanted speed difference, and scale it
            # within gameplay limits.
            wanted_speed_vector = mover.translation / dt
            if inertia.delta_inputs:
                delta_v = wanted_speed_vector
            else:
                delta_v = wanted_speed_vector - last_speed_vector
            max_delta_v = inertia.acceleration * dt
            if delta_v.length() > max_delta_v:
                capped_delta_v = delta_v / delta_v.length() * max_delta_v
            else:
                capped_delta_v = delta_v

            mover.translation = (last_speed_vector + capped_delta_v) * dt

            if inertia.ignore_z:
                mover.translation.z = old_z


class Frictioning(System):
    '''
    Applies a slow-down to the mover.
    '''
    entity_filters = {
        'mover': and_filter([
            Clock,
            Mover,
            FrictionalMovement,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['mover']:
            dt = entity[Clock].game_time
            mover = entity[Mover]
            friction = entity[FrictionalMovement]

            mover.translation *= 0.5 ** (dt / friction.half_life)


class Bumping(CollisionSystem):
    '''
        Stop the mover from moving through solid geometry.

        Components used :func:`wecs.core.and_filter` 'mover'
            | :class:`wecs.panda3d.model.Scene`
            | :class:`wecs.panda3d.mover.Mover`
            | :class:`wecs.panda3d.mover.BumpingMovement`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.model.Model`
    '''
    entity_filters = {
        'mover': and_filter([
            Proxy('scene_node'),
            Proxy('mover_node'),
            Clock,
            Mover,
            BumpingMovement,
        ]),
    }
    proxies = {
        'mover_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
    }

    def enter_filter_mover(self, entity):
        movement = entity[BumpingMovement]
        self.init_sensors(entity, movement)
        bumper = movement.solids['bumper']
        node = bumper['node']
        movement.queue.add_collider(node, node)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['mover']:
            scene_proxy = self.proxies['scene_node']
            scene = entity[scene_proxy.component_type]
            scene_node = scene_proxy.field(entity)
            mover = entity[Mover]
            movement = entity[BumpingMovement]
            bumper = movement.solids['bumper']
            node = bumper['node']
            node.set_pos(mover.translation)
            movement.traverser.traverse(scene_node)
            mover.translation = node.get_pos()


class Falling(CollisionSystem):
    '''
        Stop the mover from falling through solid geometry.

        Components used :func:`wecs.core.and_filter` 'mover'
            | :class:`wecs.panda3d.mover.Mover`
            | :class:`wecs.panda3d.mover.FallingMovement`
            | :class:`wecs.panda3d.model.Clock`
            | :class:`wecs.panda3d.model.Model`
    '''
    entity_filters = {
        'mover': and_filter([
            Proxy('scene_node'),
            Proxy('mover_node'),
            Clock,
            Mover,
            FallingMovement,
        ]),
    }
    proxies = {
        'mover_node': ProxyType(Model, 'node'),
        'scene_node': ProxyType(Model, 'parent'),
    }

    def enter_filter_mover(self, entity):
        self.init_sensors(entity, entity[FallingMovement])

    def update(self, entities_by_filter):
        for entity in entities_by_filter['mover']:
            # Adjust the falling inertia by gravity, and position the
            # lifter collider.
            self.predict_falling(entity)
            # Find collisions with the ground.
            self.run_sensors(entity, entity[FallingMovement])
            # Adjust the mover's intended translation so that his
            # falling is stoppedby the ground.
            self.fall_and_land(entity)

    def predict_falling(self, entity):
        mover = entity[Mover]
        model_proxy = self.proxies['mover_node']
        model = entity[model_proxy.component_type]
        model_node = model_proxy.field(entity)
        scene_proxy = self.proxies['scene_node']
        scene = entity[scene_proxy.component_type]
        scene_node = scene_proxy.field(entity)

        clock = entity[Clock]
        controller = entity[Mover]
        falling_movement = entity[FallingMovement]

        # Adjust inertia by gravity
        frame_gravity = mover.gravity * clock.game_time
        falling_movement.inertia += frame_gravity

        # Adjust lifter collider by inertia
        frame_inertia = falling_movement.inertia * clock.game_time
        lifter = falling_movement.solids['lifter']
        node = lifter['node']
        node.set_pos(lifter['center'] + controller.translation + frame_inertia)

    def fall_and_land(self, entity):
        falling_movement = entity[FallingMovement]
        clock = entity[Clock]
        controller = entity[Mover]

        falling_movement.ground_contact = False
        frame_falling = falling_movement.inertia * clock.game_time
        if len(falling_movement.contacts) > 0:
            lifter = falling_movement.solids['lifter']['node']
            center = falling_movement.solids['lifter']['center']
            radius = falling_movement.solids['lifter']['radius']
            height_corrections = []
            for contact in falling_movement.contacts:
                if contact.get_surface_normal(lifter).get_z() > 0.0:
                    contact_point = contact.get_surface_point(lifter) - center
                    x = contact_point.get_x()
                    y = contact_point.get_y()
                    # x**2 + y**2 + z**2 = radius**2
                    # z**2 = radius**2 - (x**2 + y**2)
                    expected_z = -sqrt(radius ** 2 - (x ** 2 + y ** 2))
                    actual_z = contact_point.get_z()
                    height_corrections.append(actual_z - expected_z)
            if height_corrections:
                frame_falling += Vec3(0, 0, max(height_corrections))
                falling_movement.inertia = Vec3(0, 0, 0)
                falling_movement.ground_contact = True

        # Now we know how falling / lifting influences the mover move
        controller.translation += frame_falling


# Transcribe the final intended movement to the model, making it an
# actual movement.

class ExecuteMovement(System):
    '''
    Transcribe the final intended movement to the model, making it an actual movement.

        Components used :func:`wecs.core.and_filter` 'mover'
            | :class:`wecs.panda3d.mover.Mover`
            | :class:`wecs.panda3d.model.Model`
            | :class:`wecs.panda3d.model.Clock`
    '''
    entity_filters = {
        'mover': and_filter([
            Proxy('mover_node'),
            Clock,
            Mover,
        ]),
    }
    proxies = {'mover_node': ProxyType(Model, 'node')}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['mover']:
            model_proxy = self.proxies['mover_node']
            model = entity[model_proxy.component_type]
            mover = entity[Mover]
            dt = entity[Clock].game_time

            # Translation: Simple self-relative movement for now.
            model_node = model_proxy.field(entity)
            model_node.set_pos(model_node, mover.translation)
            mover.last_translation_speed = mover.translation / dt

            # Rotation
            if mover.clamp_pitch:
                # Adjust intended pitch until it won't move you over a pole.
                preclamp_pitch = model_node.get_p() + mover.rotation.y
                clamped_pitch = max(min(preclamp_pitch, 89.9), -89.9)
                mover.rotation.y += clamped_pitch - preclamp_pitch

            model_node.set_hpr(model_node, mover.rotation)
            mover.last_rotation_speed = mover.rotation / dt

