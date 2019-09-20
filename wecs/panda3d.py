from dataclasses import field

from panda3d.core import Point2
from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import KeyboardButton
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode

from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from wecs.core import World
from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.core import UID


class ECSShowBase(ShowBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.ecs_world = World()

    def add_system(self, system, sort):
        self.ecs_world.add_system(system, sort)
        task = base.task_mgr.add(
            self.run_system,
            repr(system),
            extraArgs=[system],
            sort=sort,
        )
        return task

    def run_system(self, system):
        base.ecs_world.update_system(system)
        return Task.cont


@Component()
class Model:
    model_name: str = ''
    node: NodePath = None


@Component()
class Actor:
    model_name: str


@Component()
class Scene:
    node: NodePath


@Component()
class Position:
    value: Vec3 = field(default_factory=lambda:Vec3(0,0,0))


# Clock

@Component()
class Clock:
    clock: object
    timestep: float = 0.0
    max_timestep: float = 1.0/30


class DetermineTimestep(System):
    entity_filters = {
        'clock': and_filter([Clock]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['clock']:
            clock = entity[Clock]
            dt = clock.clock.dt
            max_timestep = clock.max_timestep
            if dt > max_timestep:
                dt = max_timestep
            clock.timestep = dt


# Bullet physics

@Component()
class PhysicsWorld:
    timestep: float = 0.0
    world: BulletWorld = field(default_factory=BulletWorld)


@Component()
class PhysicsBody:
    node: NodePath = None
    body: NodePath = field(default_factory=BulletRigidBodyNode)
    timestep: float = 0.0
    world: UID = None
    _world: UID = None
    scene: UID = None
    _scene: UID = None


# Loading / reparenting / destroying models

class LoadModels(System):
    entity_filters = {
        'model': and_filter([
            Model,
            Position,
            or_filter([
                Scene,
                PhysicsBody,
            ]),
        ]),
    }

    # TODO
    # Only Model is needed for loading, which then could be done
    # asynchronously.
    def init_entity(self, filter_name, entity):
        # Load
        model = entity[Model]
        if model.node is None:
            model.node = base.loader.load_model(model.model_name)

        # Load hook
        self.post_load_hook(model.node, entity)
        # Attach to PhysicsBody or Scene; former takes precedence.
        if PhysicsBody in entity:
            parent = entity[PhysicsBody].node
        else:
            parent = entity[Scene].node
        model.node.reparent_to(parent)
        model.node.set_pos(entity[Position].value)

    # TODO
    # Destroy node if and only if the Model is removed.
    def destroy_entity(self, filter_name, entity, component):
        # Remove from scene
        if isinstance(component, Model):
            component.node.destroy_node()
        else:
            entity.get_component(Model).node.destroy_node()

    def post_load_hook(self, node, entity):
        pass

            
# Bullet physics

class SetUpPhysics(System):
    entity_filters = {
        'world': and_filter([PhysicsWorld]),
        'body': and_filter([PhysicsBody]),
    }

    def init_entity(self, filter_name, entity):
        if filter_name == 'body':
            body = entity[PhysicsBody]
            body.node = NodePath(body.body)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['body']:
            body = entity[PhysicsBody]
            # Has the physics world simulating this entity changed?
            if body.world != body._world:
                if body._world is not None:
                    self.world[body._world][PhysicsWorld].remove_rigid_body()
                    body._world = None
                if body.world is not None:
                    world_cmpt = self.world[body.world][PhysicsWorld]
                    world_cmpt.world.attach_rigid_body(body.body)
                    if Position in entity:
                        body.node.set_pos(entity[Position].value)
                    body._world = body.world
            # Has the scene that this node is attached to changed?
            if body.scene != body._scene:
                scene = self.world[body.scene][Scene]
                body.node.reparent_to(scene.node)
                body._scene = body.scene

    def destroy_entity(self, filter_name, entity, components_by_type):
        pass


class DeterminePhysicsTimestep(System):
    entity_filters = {
        # FIXME: PhysicsWorld.clockshould be an entity._uid
        # (or None if the same)
        'world': and_filter([PhysicsWorld, Clock]),
        'body': and_filter([PhysicsBody]),
    }

    def update(self, entities_by_filter):
        timesteps = {}
        for entity in entities_by_filter['world']:
            world = entity[PhysicsWorld]
            world.timestep = entity[Clock].timestep
            timesteps[entity._uid] = world.timestep
        for entity in entities_by_filter['body']:
            body = entity[PhysicsBody]
            if body.world in timesteps:
                body.timestep = timesteps[body.world]


class DoPhysics(System):
    entity_filters = {
        'world': and_filter([PhysicsWorld]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['world']:
            world = entity.get_component(PhysicsWorld)
            world.world.do_physics(world.timestep)


# Camera controller

@Component()
class ZeroCamera:
    camera: NodePath
    dirty: bool = True


@Component()
class FirstPersonCamera:
    camera: NodePath
    anchor_name: str = None


# TODO:
#   Rotate-around-character support
#   Adjust distance so that the near plane is in front of level geometry
@Component()
class ThirdPersonCamera:
    camera: NodePath
    distance: float = 10.0
    height: float = 3.0
    focus_height: float = 2.0
    dirty: bool = True


class UpdateCameras(System):
    entity_filters = {
        '1stPerson': and_filter([
            FirstPersonCamera,
            Model,
        ]),
        '3rdPerson': and_filter([
            ThirdPersonCamera,
            Model,
        ]),
    }

    def init_entity(self, filter_name, entity):
        model = entity[Model]
        if filter_name == '1stPerson':
            camera = entity[FirstPersonCamera]
            if camera.anchor_name is None:
                camera.camera.reparent_to(model.node)
            else:
                camera.camera.reparent_to(model.node.find(camera.anchor_name))
            camera.camera.set_pos(0, 0, 0)
            camera.camera.set_hpr(0, 0, 0)
        elif filter_name == '3rdPerson':
            camera = entity[ThirdPersonCamera]
            camera.camera.reparent_to(model.node)
            camera.camera.set_pos(0, -camera.distance, camera.height)
            camera.camera.look_at(0, 0, camera.focus_height)

    def update(self, entities_by_filter):
        # If the camera needs to move relative to the model,
        # put the code for the here.
        # for entity in entities_by_filter['camType']:
        pass


# Character controller

from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionSphere
from panda3d.core import CollisionNode


@Component()
class MovementSensors:
    tag_name: str = 'collision_sensors' # FIXME: Symbolify
    solids: dict = field(default_factory=lambda:dict())
    contacts: dict = field(default_factory=lambda:dict())
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser())
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
    moves: dict = field(default_factory=lambda:dict())
    debug: bool = False


@Component()
class CharacterController:
    heading: float = 0.0
    pitch: float= 0.0
    move_x: float = 0.0
    move_y: float = 0.0
    max_heading: float = 90.0
    max_pitch: float= 90.0
    max_move_x: float = 100.0
    max_move_y: float = 100.0
    translation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))
    rotation: Vec3 = field(default_factory=lambda:Vec3(0, 0, 0))


@Component()
class FallingMovement:
    gravity: Vec3 = field(default_factory=lambda:Vec3(0, 0, -9.81))


@Component()
class CollisionSensors:
    tag_name: str = 'collision_sensors' # FIXME: Symbolify
    solids: dict = field(default_factory=lambda:dict())
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser())
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
    debug: bool = False


#

class CollisionSystem(System):
    def init_sensors(self, sensors, scene, model):
        if sensors.debug:
            sensors.traverser.show_collisions(scene.node)
        
        for tag, solid in sensors.solids.items():
            solid['tag'] = tag
            if solid['shape'] is CollisionSphere:
                self.add_sphere(solid, sensors, model)

    def add_sphere(self, solid, sensors, model):
        shape = CollisionSphere(solid['center'], solid['radius'])
        node = NodePath(CollisionNode(sensors.tag_name))
        node.node().add_solid(shape)
        node.reparent_to(model.node)
        sensors.traverser.add_collider(node, sensors.queue)
        node.set_python_tag(sensors.tag_name, solid['tag'])
        solid['node'] = node
        if sensors.debug:
            node.show()

    # def destroy_entity(self, filter_name, entity, component):
    #     if isinstance(component, MoveChecker):
    #         checker = component
    #     else:
    #         checker = entity[MoveChecker]
    #     if isinstance(component, CharacterHull):
    #         hull = component
    #     else:
    #         hull = entity[CharacterHull]
    #     sensors.traverser.remove_collider(hull.node)
    #     hull.solid.destroy()
    #     hull.node.destroy()

    def run_sensors(self, sensors, scene):
        sensors.contacts = {tag: [] for tag in sensors.solids.keys()}
        sensors.traverser.traverse(scene.node)
        sensors.queue.sort_entries()
        sensors.queue.sort_entries()
        for entry in sensors.queue.entries:
            tag = entry.from_node.get_python_tag(sensors.tag_name)
            sensors.contacts[tag].append(entry)


class CheckMovementSensors(CollisionSystem):
    entity_filters = {
        'sensors': and_filter([
            MovementSensors,
            Model,
            Scene,
        ]),
    }

    def init_entity(self, filter_name, entity):
        sensors = entity[MovementSensors]
        scene = entity[Scene]
        model = entity[Model]
        self.init_sensors(sensors, scene, model)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['sensors']:
            sensors = entity[MovementSensors]
            scene = entity[Scene]
            self.run_sensors(sensors, scene)


class UpdateCharacter(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Model,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            dt = entity[Clock].timestep
            controller = entity[CharacterController]
            model = entity[Model]

            controller.translation = Vec3(
                controller.move_x * controller.max_move_x * dt,
                controller.move_y * controller.max_move_y * dt,
                0,
            )
            
            heading_delta = controller.heading * controller.max_heading * dt
            preclamp_pitch = model.node.get_p() + controller.pitch * controller.max_pitch * dt
            clamped_pitch = max(min(preclamp_pitch, 89.9), -89.9)
            pitch_delta = clamped_pitch - preclamp_pitch
            controller.rotation = Vec3(
                heading_delta,
                pitch_delta,
                0,
            )


class PredictFalling(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            CollisionSensors,
            FallingMovement,
            Model,
            Scene,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            model = entity[Model]
            scene = entity[Scene]
            clock = entity[Clock]

            gravity = entity[FallingMovement].gravity * clock.timestep
            local_gravity = model.node.get_relative_vector(
                scene.node,
                gravity,
            )

            sensors = entity[CollisionSensors]
            controller = entity[CharacterController]
            movement = controller.translation
            if 'lifter' in sensors.solids.keys():
                lifter = sensors.solids['lifter']
                node = lifter['node']
                node.set_pos(lifter['center'] + movement + local_gravity)


class CheckCollisionSensors(CollisionSystem):
    entity_filters = {
        'sensors': and_filter([
            CollisionSensors,
            Model,
            Scene,
        ]),
    }

    def init_entity(self, filter_name, entity):
        sensors = entity[CollisionSensors]
        scene = entity[Scene]
        model = entity[Model]
        self.init_sensors(sensors, scene, model)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['sensors']:
            sensors = entity[CollisionSensors]
            scene = entity[Scene]
            self.run_sensors(sensors, scene)


class ExecuteFalling(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            CollisionSensors,
            FallingMovement,
            Model,
            Scene,
            Clock,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            sensors = entity[CollisionSensors]
            controller = entity[CharacterController]
            model = entity[Model]
            scene = entity[Scene]
            clock = entity[Clock]

            # FIXME: This duplicates the prediction. We know that already.
            gravity = entity[FallingMovement].gravity * clock.timestep
            local_gravity = model.node.get_relative_vector(
                scene.node,
                gravity,
            )

            # if len(sensors.contacts['lifter']) > 0:
            #     print(len(sensors.contacts['lifter']))
            #     for contact in sensors.contacts['lifter']:
            #         lifter = sensors.solids['lifter']['node']
            #         contact_point = contact.get_surface_point(lifter)
            #         import pdb; pdb.set_trace()
            #         falling_component = local_gravity
            if len(sensors.contacts['lifter']) > 0:
                contact = sensors.contacts['lifter'][0]
                lifter = sensors.solids['lifter']['node']
                center = sensors.solids['lifter']['center']
                radius = sensors.solids['lifter']['radius']
                contact_point = contact.get_surface_point(lifter) - center
                # import pdb; pdb.set_trace()
                local_gravity += Vec3(0, 0, contact_point.get_z() + radius)

            controller.translation += local_gravity
            

class ExecuteMovement(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Model,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            model = entity[Model]
            controller = entity[CharacterController]
            model.node.set_pos(model.node, controller.translation)
            model.node.set_hpr(model.node, controller.rotation)
    

# Input controller

@Component()
class Input:
    pass


class AcceptInput(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Input,
        ]),
    }

    def init_entity(self, filter_name, entity):
        base.win.movePointer(
            0,
            int(base.win.getXSize() / 2),
            int(base.win.getYSize() / 2),
        )
        #entity[Input].last_mouse_pos = None

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            character.move_x = 0.0
            character.move_y = 0.0
            character.heading = 0.0
            character.pitch = 0.0

            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("w")):
                character.move_y += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("s")):
                character.move_y -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("a")):
                character.move_x -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("d")):
                character.move_x += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.up()):
                character.pitch += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.down()):
                character.pitch -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.left()):
                character.heading += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.right()):
                character.heading -= 1

            # if base.mouseWatcherNode.has_mouse():
            #     mouse_pos = base.mouseWatcherNode.get_mouse()
            #     character.heading = mouse_pos.get_x() * -character.max_heading
            #     character.pitch = mouse_pos.get_y() * character.max_pitch
            # else:
            #     mouse_pos = None
            # base.win.movePointer(
            #     0,
            #     int(base.win.getXSize() / 2),
            #     int(base.win.getYSize() / 2),
            # )
            # entity[Input].last_mouse_pos = mouse_pos
